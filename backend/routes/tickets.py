"""Karte — kupnja preko Stripea, potvrda, pregled, otkazivanje, admin statistike."""

import uuid
from datetime import datetime

import stripe
from bson import ObjectId
from flask import Blueprint, jsonify, request

import stripe_service
from auth_utils import (
    current_club_id, current_role, current_user_id, role_required, serialize,
)
from db import events_col, tickets_col, users_col
from payments import confirm_ticket_purchase

tickets_bp = Blueprint("tickets", __name__, url_prefix="/api")


@tickets_bp.route("/tickets/purchase", methods=["POST"])
@role_required("user")
def purchase_ticket():
    """Kreira pending kartu + Stripe PaymentIntent; vraća client_secret."""
    data = request.get_json(silent=True) or {}
    event_id = data.get("event_id")
    ticket_type_id = data.get("ticket_type_id")
    if not event_id or not ticket_type_id:
        return jsonify({"error": "event_id i ticket_type_id su obavezni"}), 400

    event = events_col.find_one({
        "_id": ObjectId(event_id),
        "is_published": True,
        "is_cancelled": {"$ne": True},
    })
    if not event:
        return jsonify({"error": "Event ne postoji ili nije dostupan"}), 404

    ticket_type = next(
        (t for t in event.get("ticket_types", []) if t["id"] == ticket_type_id), None
    )
    if not ticket_type or not ticket_type.get("is_active", True):
        return jsonify({"error": "Tip karte ne postoji ili nije aktivan"}), 404

    now = datetime.utcnow()
    if ticket_type.get("sale_start") and now < ticket_type["sale_start"]:
        return jsonify({"error": "Prodaja još nije počela"}), 409
    if ticket_type.get("sale_end") and now > ticket_type["sale_end"]:
        return jsonify({"error": "Prodaja je završila"}), 409

    user = users_col.find_one({"_id": current_user_id()})
    if not user:
        return jsonify({"error": "Korisnik ne postoji"}), 404

    # Atomarno rezerviraj kvotu — guard u array_filteru sprječava overselling
    # pri istovremenim kupnjama (kvota se vraća ako plaćanje ne uspije/istekne)
    claimed = events_col.update_one(
        {"_id": event["_id"]},
        {"$inc": {"ticket_types.$[t].sold_quantity": 1}},
        array_filters=[{
            "t.id": ticket_type_id,
            "t.sold_quantity": {"$lt": ticket_type["total_quantity"]},
        }],
    )
    if not claimed.modified_count:
        return jsonify({"error": "Karte ovog tipa su rasprodane"}), 409

    def _release_quota():
        events_col.update_one(
            {"_id": event["_id"]},
            {"$inc": {"ticket_types.$[t].sold_quantity": -1}},
            array_filters=[{"t.id": ticket_type_id}],
        )

    # Osiguraj Stripe customera (Apple Pay / Google Pay / kartice)
    try:
        if not user.get("stripe_customer_id"):
            customer_id = stripe_service.get_or_create_stripe_customer(user)
            users_col.update_one(
                {"_id": user["_id"]}, {"$set": {"stripe_customer_id": customer_id}}
            )
            user["stripe_customer_id"] = customer_id

        intent = stripe_service.create_ticket_payment_intent(
            ticket_type["price"], user, event_id, ticket_type_id
        )
    except Exception as exc:
        _release_quota()
        return jsonify({"error": f"Stripe greška: {exc}"}), 502

    ticket = {
        "user_id": user["_id"],
        "event_id": event["_id"],
        "club_id": event["club_id"],
        "ticket_type_id": ticket_type_id,
        "ticket_type_name": ticket_type["name"],
        "price_paid": float(ticket_type["price"]),
        "qr_code": str(uuid.uuid4()),
        "status": "pending",
        "checked_in_at": None,
        "checked_in_by": None,
        "stripe_payment_intent_id": intent.id,
        "purchased_at": datetime.utcnow(),
    }
    result = tickets_col.insert_one(ticket)

    return jsonify({
        "ticket_id": str(result.inserted_id),
        "client_secret": intent.client_secret,
        "publishable_key": stripe_service.STRIPE_PUBLISHABLE_KEY,
        "amount": ticket["price_paid"],
    }), 201


@tickets_bp.route("/tickets/confirm", methods=["POST"])
def confirm_ticket():
    """
    Potvrda kupnje. Primarno je potvrđuje Stripe webhook; ova ruta služi kao
    fallback u lokalnom razvoju — dohvaća PaymentIntent i provjerava status.
    """
    data = request.get_json(silent=True) or {}
    pi_id = data.get("payment_intent_id")
    if not pi_id:
        return jsonify({"error": "payment_intent_id je obavezan"}), 400
    try:
        intent = stripe.PaymentIntent.retrieve(pi_id)
    except Exception as exc:
        return jsonify({"error": f"Stripe greška: {exc}"}), 502

    if intent.status != "succeeded":
        return jsonify({"error": f"Plaćanje nije uspjelo (status: {intent.status})"}), 409

    confirmed = confirm_ticket_purchase(intent)
    return jsonify({"success": bool(confirmed)})


@tickets_bp.route("/tickets/my", methods=["GET"])
@role_required("user")
def my_tickets():
    tickets = list(
        tickets_col.find({"user_id": current_user_id()})
        .sort("purchased_at", -1).limit(200)
    )
    event_ids = list({t["event_id"] for t in tickets})
    events = {
        e["_id"]: serialize(e) for e in events_col.find(
            {"_id": {"$in": event_ids}},
            {"name": 1, "date": 1, "cover_image": 1, "club_id": 1},
        )
    }
    enriched = []
    for t in tickets:
        doc = serialize(t)
        event = events.get(t["event_id"])
        if event:
            doc["event"] = event
        enriched.append(doc)
    return jsonify({"tickets": enriched})


@tickets_bp.route("/tickets/<ticket_id>/cancel", methods=["POST"])
@role_required("user")
def cancel_ticket(ticket_id):
    ticket = tickets_col.find_one({
        "_id": ObjectId(ticket_id), "user_id": current_user_id(),
    })
    if not ticket:
        return jsonify({"error": "Karta ne postoji"}), 404

    event = events_col.find_one({"_id": ticket["event_id"]}, {"date": 1})
    if event and event["date"] <= datetime.utcnow():
        return jsonify({"error": "Event je već počeo — otkazivanje nije moguće"}), 409

    # Atomarno preuzmi otkazivanje — paralelni zahtjevi ne mogu dvaput refundirati
    claimed = tickets_col.find_one_and_update(
        {"_id": ticket["_id"], "status": {"$in": ["valid", "pending"]}},
        {"$set": {"status": "cancelled", "cancelled_at": datetime.utcnow()}},
    )
    if not claimed:
        return jsonify(
            {"error": f"Kartu nije moguće otkazati (status: {ticket['status']})"}
        ), 409

    # Kvota je rezervirana pri kupnji (i za pending) — uvijek je oslobodi
    events_col.update_one(
        {"_id": ticket["event_id"]},
        {"$inc": {"ticket_types.$[t].sold_quantity": -1}},
        array_filters=[{"t.id": ticket["ticket_type_id"]}],
    )

    refunded = False
    if claimed["status"] == "valid" and claimed.get("stripe_payment_intent_id"):
        try:
            stripe_service.refund_payment_intent(claimed["stripe_payment_intent_id"])
            refunded = True
            tickets_col.update_one(
                {"_id": ticket["_id"]}, {"$set": {"refund_status": "refunded"}}
            )
        except Exception as exc:
            tickets_col.update_one(
                {"_id": ticket["_id"]},
                {"$set": {"refund_status": "failed", "refund_error": str(exc)}},
            )
            return jsonify(
                {"error": f"Karta je otkazana, ali refund nije uspio: {exc}"}
            ), 502

    return jsonify({"success": True, "refunded": refunded})


def _assert_admin_event(event_id):
    event = events_col.find_one({"_id": ObjectId(event_id)})
    if not event:
        return None, (jsonify({"error": "Event ne postoji"}), 404)
    if current_role() != "superadmin" and current_club_id() != event["club_id"]:
        return None, (jsonify({"error": "Nemate ovlasti nad ovim eventom"}), 403)
    return event, None


@tickets_bp.route("/events/<event_id>/tickets", methods=["GET"])
@role_required("admin", "superadmin")
def event_tickets(event_id):
    """Prodane karte eventa s podacima o kupcu."""
    event, err = _assert_admin_event(event_id)
    if err:
        return err

    limit = min(int(request.args.get("limit", 200)), 1000)
    tickets = list(tickets_col.find({
        "event_id": event["_id"],
        "status": {"$in": ["valid", "checked_in"]},
    }).sort("purchased_at", -1).limit(limit))

    user_ids = list({t["user_id"] for t in tickets})
    users = {
        u["_id"]: u for u in users_col.find(
            {"_id": {"$in": user_ids}}, {"name": 1, "email": 1, "phone": 1}
        )
    }
    enriched = []
    for t in tickets:
        doc = serialize(t)
        doc["user"] = serialize(users.get(t["user_id"], {}))
        enriched.append(doc)
    return jsonify({"tickets": enriched, "count": len(enriched)})


@tickets_bp.route("/events/<event_id>/ticket-stats", methods=["GET"])
@role_required("admin", "superadmin")
def event_ticket_stats(event_id):
    """Statistike prodaje po tipu karte + ukupni prihod."""
    event, err = _assert_admin_event(event_id)
    if err:
        return err

    per_type = []
    for tt in event.get("ticket_types", []):
        per_type.append({
            "id": tt["id"],
            "name": tt["name"],
            "price": tt["price"],
            "total_quantity": tt["total_quantity"],
            "sold_quantity": tt["sold_quantity"],
            "remaining": tt["total_quantity"] - tt["sold_quantity"],
            "revenue": round(tt["price"] * tt["sold_quantity"], 2),
        })

    checked_in = tickets_col.count_documents(
        {"event_id": event["_id"], "status": "checked_in"}
    )
    return jsonify({
        "event_id": event_id,
        "ticket_types": per_type,
        "total_sold": sum(t["sold_quantity"] for t in per_type),
        "total_revenue": round(sum(t["revenue"] for t in per_type), 2),
        "checked_in": checked_in,
    })
