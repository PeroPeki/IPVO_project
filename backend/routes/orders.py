"""Narudžbe pića — korisnički flow, konobarski prikaz, barski zaslon, plaćanje."""

from bson import ObjectId
from flask import Blueprint, jsonify, request

import stripe_service
from auth_utils import (
    current_club_id, current_role, current_user_id, role_required, serialize,
)
from db import drink_orders_col, events_col, users_col, waiters_col
from order_service import (
    OrderError,
    cancel_order,
    place_order,
    waiter_accept_order,
    waiter_collect_cash,
    waiter_deliver_order,
)

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")


@orders_bp.route("", methods=["POST"])
@role_required("user")
def create_order():
    data = request.get_json(silent=True) or {}
    reservation_id = data.get("reservation_id")
    items = data.get("items") or []
    payment_method = data.get("payment_method", "card")

    if not reservation_id:
        return jsonify({"error": "reservation_id je obavezan"}), 400
    if payment_method not in ("card", "apple_pay", "google_pay", "cash"):
        return jsonify({"error": "Nepodržan način plaćanja"}), 400

    try:
        order_id, order = place_order(
            current_user_id(), reservation_id, items, payment_method
        )
    except OrderError as exc:
        return jsonify({"error": str(exc)}), 409

    response = {
        "order_id": order_id,
        "subtotal": order["subtotal"],
        "coupon_applied": order["coupon_applied"],
        "total": order["total"],
        "payment_status": order["payment_status"],
    }

    # Kartično plaćanje: odmah pripremi PaymentIntent (ako ostane iznosa nakon kupona)
    if payment_method != "cash" and order["total"] > 0:
        user = users_col.find_one({"_id": current_user_id()})
        try:
            intent = stripe_service.create_drink_payment_intent(
                order["total"], user, order_id
            )
            drink_orders_col.update_one(
                {"_id": ObjectId(order_id)},
                {"$set": {"stripe_payment_intent_id": intent.id}},
            )
            response["client_secret"] = intent.client_secret
            response["publishable_key"] = stripe_service.STRIPE_PUBLISHABLE_KEY
        except Exception as exc:
            return jsonify({"error": f"Stripe greška: {exc}"}), 502
    elif order["total"] == 0:
        # Kupon pokrio cijelu narudžbu
        drink_orders_col.update_one(
            {"_id": ObjectId(order_id)}, {"$set": {"payment_status": "paid"}}
        )
        response["payment_status"] = "paid"

    return jsonify(response), 201


@orders_bp.route("/waiter", methods=["GET"])
@role_required("waiter")
def waiter_orders():
    """
    Aktivne narudžbe konobarove sekcije (placed + accepted + preparing),
    plus dostavljene gotovinske koje još čekaju naplatu.
    """
    waiter = waiters_col.find_one({"_id": current_user_id()})
    if not waiter:
        return jsonify({"error": "Konobar ne postoji"}), 404

    query = {
        "club_id": waiter["club_id"],
        "$and": [
            {"$or": [
                {"waiter_id": waiter["_id"]},
                {"section_id": {"$in": waiter.get("assigned_sections", [])}},
            ]},
            {"$or": [
                {"order_status": {"$in": ["placed", "accepted", "preparing"]}},
                {"order_status": "delivered", "payment_status": "cash_pending"},
            ]},
        ],
    }
    orders = [serialize(o) for o in drink_orders_col.find(query).sort("created_at", 1)]
    return jsonify({"orders": orders, "count": len(orders)})


@orders_bp.route("/<order_id>/accept", methods=["PUT"])
@role_required("waiter")
def accept_order(order_id):
    try:
        order = waiter_accept_order(order_id, current_user_id())
    except OrderError as exc:
        return jsonify({"error": str(exc)}), 409
    return jsonify({"success": True, "order": serialize(order)})


@orders_bp.route("/<order_id>/deliver", methods=["PUT"])
@role_required("waiter")
def deliver_order(order_id):
    try:
        order = waiter_deliver_order(order_id, current_user_id())
    except OrderError as exc:
        return jsonify({"error": str(exc)}), 409
    return jsonify({"success": True, "order": serialize(order)})


@orders_bp.route("/<order_id>/collect-cash", methods=["PUT"])
@role_required("waiter", "admin", "superadmin")
def collect_cash(order_id):
    """Potvrda naplate gotovine — bez ovoga gotovinski prihod ne ulazi u izvještaje."""
    try:
        order = waiter_collect_cash(order_id, current_user_id())
    except OrderError as exc:
        return jsonify({"error": str(exc)}), 409
    return jsonify({"success": True, "order": serialize(order)})


@orders_bp.route("/<order_id>/cancel", methods=["PUT"])
@role_required("user", "waiter", "admin")
def cancel_order_route(order_id):
    user_id = current_user_id() if current_role() == "user" else None
    try:
        order = cancel_order(order_id, user_id)
    except OrderError as exc:
        return jsonify({"error": str(exc)}), 409
    return jsonify({"success": True, "order": serialize(order)})


@orders_bp.route("/<order_id>/payment", methods=["POST"])
@role_required("user")
def pay_order(order_id):
    """Naknadno plaćanje narudžbe — Stripe (kartica/wallet) ili gotovina konobaru."""
    data = request.get_json(silent=True) or {}
    method = data.get("payment_method", "card")

    order = drink_orders_col.find_one({
        "_id": ObjectId(order_id), "user_id": current_user_id(),
    })
    if not order:
        return jsonify({"error": "Narudžba ne postoji"}), 404
    if order["payment_status"] == "paid":
        return jsonify({"error": "Narudžba je već plaćena"}), 409

    if method == "cash":
        drink_orders_col.update_one(
            {"_id": order["_id"]},
            {"$set": {"payment_method": "cash", "payment_status": "cash_pending"}},
        )
        return jsonify({"success": True, "payment_status": "cash_pending",
                        "message": "Gotovinu naplaćuje konobar pri dostavi"})

    user = users_col.find_one({"_id": current_user_id()})
    try:
        intent = stripe_service.create_drink_payment_intent(
            order["total"], user, order_id
        )
    except Exception as exc:
        return jsonify({"error": f"Stripe greška: {exc}"}), 502

    drink_orders_col.update_one(
        {"_id": order["_id"]},
        {"$set": {"payment_method": method,
                  "payment_status": "pending",
                  "stripe_payment_intent_id": intent.id}},
    )
    return jsonify({
        "client_secret": intent.client_secret,
        "publishable_key": stripe_service.STRIPE_PUBLISHABLE_KEY,
        "amount": order["total"],
    })


@orders_bp.route("/bar/<event_id>", methods=["GET"])
@role_required("waiter", "hostess", "admin", "superadmin")
def bar_screen(event_id):
    """Barski zaslon — sve aktivne narudžbe eventa."""
    orders = [
        serialize(o) for o in drink_orders_col.find({
            "event_id": ObjectId(event_id),
            "order_status": {"$in": ["placed", "accepted", "preparing"]},
        }).sort("created_at", 1)
    ]
    return jsonify({"orders": orders, "count": len(orders)})


@orders_bp.route("/my", methods=["GET"])
@role_required("user")
def my_orders():
    orders = list(
        drink_orders_col.find({"user_id": current_user_id()})
        .sort("created_at", -1).limit(50)
    )
    event_ids = list({o["event_id"] for o in orders})
    events = {
        e["_id"]: serialize(e) for e in events_col.find(
            {"_id": {"$in": event_ids}}, {"name": 1, "date": 1}
        )
    }
    enriched = []
    for o in orders:
        doc = serialize(o)
        event = events.get(o["event_id"])
        if event:
            doc["event"] = event
        enriched.append(doc)
    return jsonify({"orders": enriched})
