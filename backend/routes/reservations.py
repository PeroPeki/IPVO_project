"""Rezervacije stolova — dostupnost, kreiranje, depozit, otkazivanje, check-in."""

from bson import ObjectId
from flask import Blueprint, jsonify, request

import stripe_service
from auth_utils import (
    current_club_id, current_role, current_user_id, role_required, serialize,
)
from db import events_col, table_reservations_col, users_col
from realtime import publish
from reservation_service import (
    ACTIVE_STATUSES,
    ReservationError,
    cancel_reservation,
    checkin_reservation,
    create_reservation,
)

reservations_bp = Blueprint("reservations", __name__, url_prefix="/api/reservations")


@reservations_bp.route("/event/<event_id>", methods=["GET"])
def event_availability(event_id):
    """Dostupnost stolova za event — mapa table_id → status."""
    reservations = table_reservations_col.find(
        {"event_id": ObjectId(event_id), "status": {"$in": ACTIVE_STATUSES}},
        {"table_id": 1, "status": 1},
    )
    reserved = {r["table_id"]: r["status"] for r in reservations}
    return jsonify({"event_id": event_id, "reserved_tables": reserved})


@reservations_bp.route("", methods=["POST"])
@role_required("user")
def create_reservation_route():
    data = request.get_json(silent=True) or {}
    event_id = data.get("event_id")
    table_id = data.get("table_id")
    guests_count = int(data.get("guests_count", 1))
    if not event_id or not table_id:
        return jsonify({"error": "event_id i table_id su obavezni"}), 400

    try:
        reservation_id, deposit = create_reservation(
            current_user_id(), event_id, table_id, guests_count
        )
    except ReservationError as exc:
        return jsonify({"error": str(exc)}), 409

    publish('table_updates', {
        "event_id": str(event_id),
        "table_id": table_id,
        "status": "reserved",
    })

    return jsonify({
        "reservation_id": reservation_id,
        "deposit_required": deposit > 0,
        "deposit_amount": deposit,
        "message": (
            "Rezervacija čeka uplatu depozita" if deposit > 0
            else "Rezervacija je potvrđena"
        ),
    }), 201


@reservations_bp.route("/<reservation_id>/deposit", methods=["POST"])
@role_required("user")
def pay_deposit(reservation_id):
    """Kreira Stripe PaymentIntent za VIP depozit."""
    reservation = table_reservations_col.find_one({
        "_id": ObjectId(reservation_id), "user_id": current_user_id(),
    })
    if not reservation:
        return jsonify({"error": "Rezervacija ne postoji"}), 404
    if reservation.get("deposit_paid"):
        return jsonify({"error": "Depozit je već plaćen"}), 409
    if not reservation.get("deposit_amount"):
        return jsonify({"error": "Rezervacija ne zahtijeva depozit"}), 409

    user = users_col.find_one({"_id": current_user_id()})
    if not user.get("stripe_customer_id"):
        customer_id = stripe_service.get_or_create_stripe_customer(user)
        users_col.update_one(
            {"_id": user["_id"]}, {"$set": {"stripe_customer_id": customer_id}}
        )
        user["stripe_customer_id"] = customer_id

    try:
        intent = stripe_service.create_deposit_payment_intent(
            reservation["deposit_amount"], user, reservation_id
        )
    except Exception as exc:
        return jsonify({"error": f"Stripe greška: {exc}"}), 502

    table_reservations_col.update_one(
        {"_id": reservation["_id"]},
        {"$set": {"stripe_deposit_payment_intent": intent.id}},
    )
    return jsonify({
        "client_secret": intent.client_secret,
        "publishable_key": stripe_service.STRIPE_PUBLISHABLE_KEY,
        "amount": reservation["deposit_amount"],
        # VIP kupon upozorenje iz specifikacije
        "coupon_notice": (
            "Depozit se pretvara u kupon za piće. Kupon je vezan uz Vas osobno "
            "i ne može se dijeliti s drugim gostima."
        ),
    })


@reservations_bp.route("/<reservation_id>/cancel", methods=["POST"])
@role_required("user")
def cancel_reservation_route(reservation_id):
    try:
        reservation, refunded = cancel_reservation(reservation_id, current_user_id())
    except ReservationError as exc:
        return jsonify({"error": str(exc)}), 409

    publish('table_updates', {
        "event_id": str(reservation["event_id"]),
        "table_id": reservation["table_id"],
        "status": "free",
    })
    return jsonify({"success": True, "deposit_refunded": refunded})


@reservations_bp.route("/my", methods=["GET"])
@role_required("user")
def my_reservations():
    reservations = list(
        table_reservations_col.find({"user_id": current_user_id()})
        .sort("created_at", -1)
    )
    enriched = []
    for r in reservations:
        doc = serialize(r)
        event = events_col.find_one(
            {"_id": r["event_id"]}, {"name": 1, "date": 1, "cover_image": 1}
        )
        if event:
            doc["event"] = serialize(event)
        enriched.append(doc)
    return jsonify({"reservations": enriched})


@reservations_bp.route("/event/<event_id>/all", methods=["GET"])
@role_required("admin", "superadmin")
def event_reservations(event_id):
    """Sve rezervacije eventa (admin pregled)."""
    event = events_col.find_one({"_id": ObjectId(event_id)})
    if not event:
        return jsonify({"error": "Event ne postoji"}), 404
    if current_role() != "superadmin" and current_club_id() != event["club_id"]:
        return jsonify({"error": "Nemate ovlasti nad ovim eventom"}), 403

    reservations = list(
        table_reservations_col.find({"event_id": event["_id"]}).sort("created_at", -1)
    )
    user_ids = list({r["user_id"] for r in reservations})
    users = {
        u["_id"]: u for u in users_col.find(
            {"_id": {"$in": user_ids}}, {"name": 1, "email": 1, "phone": 1}
        )
    }
    enriched = []
    for r in reservations:
        doc = serialize(r)
        doc["user"] = serialize(users.get(r["user_id"], {}))
        enriched.append(doc)
    return jsonify({"reservations": enriched, "count": len(enriched)})


@reservations_bp.route("/<reservation_id>/checkin", methods=["PUT"])
@role_required("hostess", "admin", "superadmin")
def checkin_route(reservation_id):
    try:
        reservation = checkin_reservation(reservation_id, current_user_id())
    except ReservationError as exc:
        return jsonify({"error": str(exc)}), 409

    publish('table_updates', {
        "event_id": str(reservation["event_id"]),
        "table_id": reservation["table_id"],
        "status": "checked_in",
    })
    return jsonify({"success": True})
