"""
Logika narudžbi pića (FAZA 7).

Naručivanje je dostupno samo gostima s aktivnom rezervacijom stola.
Cijene stavki razrješavaju se server-side iz menija kluba, VIP kupon
se automatski primjenjuje, a konobar pripadajuće sekcije dobiva
narudžbu real-time putem Redis Pub/Sub → Socket.IO.
"""

from datetime import datetime

from bson import ObjectId

import stripe_service
from db import drink_orders_col, menus_col, table_reservations_col, waiters_col
from realtime import publish
from reservation_service import apply_coupon

CARD_METHODS = ["card", "apple_pay", "google_pay"]


class OrderError(Exception):
    pass


def _resolve_items(club_id, raw_items):
    """Iz {menu_item_id, quantity} parova slaže stavke s cijenama iz menija."""
    menu = menus_col.find_one({"club_id": club_id, "is_active": True})
    if not menu:
        raise OrderError("Klub nema aktivan meni")

    items_by_id = {}
    for category in menu.get("categories", []):
        for item in category.get("items", []):
            items_by_id[item["id"]] = item

    resolved = []
    for raw in raw_items:
        item = items_by_id.get(raw.get("menu_item_id"))
        if not item:
            raise OrderError(f"Stavka {raw.get('menu_item_id')} ne postoji u meniju")
        if not item.get("is_available", True):
            raise OrderError(f"Stavka '{item['name']}' trenutno nije dostupna")
        quantity = int(raw.get("quantity", 1))
        if quantity < 1:
            raise OrderError("Količina mora biti barem 1")
        resolved.append({
            "menu_item_id": item["id"],
            "name": item["name"],
            "quantity": quantity,
            "unit_price": float(item["price"]),
            "subtotal": round(float(item["price"]) * quantity, 2),
        })
    if not resolved:
        raise OrderError("Narudžba je prazna")
    return resolved


def place_order(user_id, reservation_id, raw_items, payment_method):
    """Kreira narudžbu; vraća (order_id, order_doc)."""
    reservation = table_reservations_col.find_one({
        "_id": ObjectId(reservation_id),
        "user_id": ObjectId(user_id),
        "status": {"$in": ["confirmed", "checked_in"]},
    })
    if not reservation:
        raise OrderError(
            "Nemate aktivnu rezervaciju. Naručivanje pića dostupno je samo "
            "gostima s rezerviranim stolom."
        )

    items = _resolve_items(reservation["club_id"], raw_items)
    subtotal = round(sum(i["subtotal"] for i in items), 2)
    final_total, coupon_applied = apply_coupon(reservation_id, subtotal)

    # Pronađi konobara zaduženog za sekciju stola
    waiter = waiters_col.find_one({
        "club_id": reservation["club_id"],
        "assigned_sections": reservation.get("section_id"),
        "is_active": True,
    })

    order = {
        "user_id": ObjectId(user_id),
        "club_id": reservation["club_id"],
        "event_id": reservation["event_id"],
        "table_reservation_id": ObjectId(reservation_id),
        "table_id": reservation["table_id"],
        "table_label": reservation["table_label"],
        "section_id": reservation.get("section_id"),
        "waiter_id": waiter["_id"] if waiter else None,
        "items": items,
        "subtotal": subtotal,
        "coupon_applied": coupon_applied,
        "total": final_total,
        "payment_method": payment_method,
        "payment_status": "pending" if payment_method in CARD_METHODS else "cash_pending",
        "stripe_payment_intent_id": None,
        "order_status": "placed",
        "waiter_accepted_at": None,
        "delivered_at": None,
        "created_at": datetime.utcnow(),
    }

    result = drink_orders_col.insert_one(order)
    order_id = str(result.inserted_id)

    _publish_order_update(order, order_id)
    return order_id, order


def _publish_order_update(order, order_id):
    publish('order_updates', {
        "order_id": order_id,
        "waiter_id": str(order["waiter_id"]) if order.get("waiter_id") else None,
        "event_id": str(order["event_id"]),
        "table_label": order.get("table_label"),
        "section_id": order.get("section_id"),
        "items": [
            {"name": i["name"], "quantity": i["quantity"]} for i in order.get("items", [])
        ],
        "total": order.get("total"),
        "payment_method": order.get("payment_method"),
        "payment_status": order.get("payment_status"),
        "order_status": order.get("order_status"),
    })


def _transition(order_id, updates, expected_query=None):
    query = {"_id": ObjectId(order_id)}
    if expected_query:
        query.update(expected_query)
    order = drink_orders_col.find_one_and_update(
        query, {"$set": updates}, return_document=True
    )
    if not order:
        raise OrderError("Narudžba ne postoji ili prijelaz nije dozvoljen")
    _publish_order_update(order, str(order["_id"]))
    return order


def waiter_accept_order(order_id, waiter_id):
    return _transition(
        order_id,
        {"order_status": "accepted", "waiter_id": ObjectId(waiter_id),
         "waiter_accepted_at": datetime.utcnow()},
        {"order_status": "placed"},
    )


def waiter_deliver_order(order_id, waiter_id):
    return _transition(
        order_id,
        {"order_status": "delivered", "delivered_at": datetime.utcnow()},
        {"order_status": {"$in": ["accepted", "preparing"]}},
    )


def waiter_collect_cash(order_id, waiter_id):
    """Konobar potvrđuje naplatu gotovine — narudžba postaje plaćena."""
    return _transition(
        order_id,
        {"payment_status": "paid", "paid_at": datetime.utcnow(),
         "cash_collected_by": ObjectId(waiter_id)},
        {"payment_method": "cash", "payment_status": "cash_pending"},
    )


def cancel_order(order_id, user_id=None):
    query = {
        "_id": ObjectId(order_id),
        "order_status": {"$in": ["placed", "accepted", "preparing"]},
    }
    if user_id is not None:
        query["user_id"] = ObjectId(user_id)

    # Atomarno preuzmi otkazivanje; vraća dokument PRIJE izmjene da se vidi
    # je li narudžba bila plaćena
    order = drink_orders_col.find_one_and_update(
        query,
        {"$set": {"order_status": "cancelled", "cancelled_at": datetime.utcnow()}},
    )
    if not order:
        raise OrderError("Narudžba ne postoji ili prijelaz nije dozvoljen")

    # Vrati kupon ako je bio primijenjen
    if order.get("coupon_applied"):
        table_reservations_col.update_one(
            {"_id": order["table_reservation_id"]},
            {"$inc": {"deposit_coupon_remaining": order["coupon_applied"]}},
        )

    # Kartično plaćena narudžba → Stripe refund
    payment_status = "cancelled"
    if order.get("payment_status") == "paid" and order.get("stripe_payment_intent_id"):
        try:
            stripe_service.refund_payment_intent(order["stripe_payment_intent_id"])
            payment_status = "refunded"
        except Exception as exc:
            payment_status = "refund_failed"
            drink_orders_col.update_one(
                {"_id": order["_id"]}, {"$set": {"refund_error": str(exc)}}
            )

    drink_orders_col.update_one(
        {"_id": order["_id"]}, {"$set": {"payment_status": payment_status}}
    )
    order["order_status"] = "cancelled"
    order["payment_status"] = payment_status
    _publish_order_update(order, str(order["_id"]))
    return order
