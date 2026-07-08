"""
Potvrde plaćanja — zajednička logika za Stripe webhook i ručne confirm rute.

Svaka funkcija prima Stripe PaymentIntent (dict ili objekt) čiji metadata
`type` određuje o kojem se plaćanju radi.
"""

from datetime import datetime

from bson import ObjectId

import stripe_service
from db import drink_orders_col, events_col, table_reservations_col, tickets_col
from email_service import send_ticket_confirmation
from realtime import publish
from reservation_service import confirm_vip_deposit


def confirm_ticket_purchase(pi):
    """
    payment_intent.succeeded za kupnju karte → karta postaje važeća.

    Kvota (sold_quantity) je rezervirana već pri kupnji, pa se ovdje samo
    mijenja status. Ako je karta u međuvremenu istekla (expired), pokušava
    se ponovno zauzeti kvota; ako je rasprodano, plaćanje se refundira.
    """
    pi_id = pi["id"] if isinstance(pi, dict) else pi.id
    ticket = tickets_col.find_one({"stripe_payment_intent_id": pi_id})
    if not ticket:
        return False

    status = ticket.get("status")
    if status in ("valid", "checked_in"):
        return True  # webhook retry / fallback confirm — već obrađeno

    if status == "pending":
        result = tickets_col.update_one(
            {"_id": ticket["_id"], "status": "pending"},
            {"$set": {"status": "valid"}},
        )
        if result.modified_count:
            send_ticket_confirmation(ticket)
        return True

    if status == "expired":
        # Plaćanje je stiglo nakon isteka — pokušaj ponovno zauzeti kvotu
        event = events_col.find_one({"_id": ticket["event_id"]})
        ticket_type = next(
            (t for t in (event or {}).get("ticket_types", [])
             if t["id"] == ticket["ticket_type_id"]),
            None,
        )
        if ticket_type:
            claimed = events_col.update_one(
                {"_id": ticket["event_id"]},
                {"$inc": {"ticket_types.$[t].sold_quantity": 1}},
                array_filters=[{
                    "t.id": ticket["ticket_type_id"],
                    "t.sold_quantity": {"$lt": ticket_type["total_quantity"]},
                }],
            )
            if claimed.modified_count:
                tickets_col.update_one(
                    {"_id": ticket["_id"]}, {"$set": {"status": "valid"}}
                )
                send_ticket_confirmation(ticket)
                return True

        # Rasprodano → automatski refund
        try:
            stripe_service.refund_payment_intent(pi_id)
            tickets_col.update_one(
                {"_id": ticket["_id"]}, {"$set": {"status": "refunded"}}
            )
        except Exception as exc:
            tickets_col.update_one(
                {"_id": ticket["_id"]},
                {"$set": {"refund_status": "failed", "refund_error": str(exc)}},
            )
        return False

    return False


def confirm_deposit_payment(pi):
    """payment_intent.succeeded za VIP depozit → rezervacija confirmed + kupon."""
    metadata = pi["metadata"] if isinstance(pi, dict) else pi.metadata
    reservation_id = metadata.get("reservation_id")
    if not reservation_id:
        return False
    amount = pi["amount"] if isinstance(pi, dict) else pi.amount
    pi_id = pi["id"] if isinstance(pi, dict) else pi.id

    confirmed = confirm_vip_deposit(reservation_id, amount, pi_id)

    reservation = table_reservations_col.find_one({"_id": ObjectId(reservation_id)})
    if reservation:
        publish('table_updates', {
            "event_id": str(reservation["event_id"]),
            "table_id": reservation["table_id"],
            "status": "reserved" if confirmed else "free",
        })
    return confirmed


def confirm_drink_payment(pi):
    """payment_intent.succeeded za narudžbu pića → payment_status = paid."""
    metadata = pi["metadata"] if isinstance(pi, dict) else pi.metadata
    order_id = metadata.get("order_id")
    if not order_id:
        return False

    result = drink_orders_col.find_one_and_update(
        {"_id": ObjectId(order_id)},
        {"$set": {"payment_status": "paid", "paid_at": datetime.utcnow()}},
    )
    if result:
        publish('order_updates', {
            "order_id": order_id,
            "waiter_id": str(result["waiter_id"]) if result.get("waiter_id") else None,
            "event_id": str(result["event_id"]),
            "table_label": result.get("table_label"),
            "order_status": result.get("order_status"),
            "payment_status": "paid",
        })
    return True


def handle_payment_intent_succeeded(pi):
    """Dispatch prema metadata.type — poziva se iz webhooka."""
    metadata = pi["metadata"] if isinstance(pi, dict) else pi.metadata
    payment_type = metadata.get('type')
    if payment_type == 'ticket_purchase':
        return confirm_ticket_purchase(pi)
    if payment_type == 'vip_deposit':
        return confirm_deposit_payment(pi)
    if payment_type == 'drink_order':
        return confirm_drink_payment(pi)
    return False
