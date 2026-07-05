"""Hostesa — lista gostiju, check-in karata i rezervacija, live statistike."""

import re
from datetime import datetime

from bson import ObjectId
from flask import Blueprint, jsonify, request

from auth_utils import current_user_id, role_required, serialize
from db import events_col, table_reservations_col, tickets_col, users_col
from realtime import publish
from reservation_service import ReservationError, checkin_reservation

hostess_bp = Blueprint("hostess", __name__, url_prefix="/api/hostess")

STAFF_ROLES = ("hostess", "admin", "superadmin")


@hostess_bp.route("/event/<event_id>/guests", methods=["GET"])
@role_required(*STAFF_ROLES)
def event_guests(event_id):
    """Lista gostiju (karte + rezervacije) uz pretragu po imenu/prezimenu."""
    oid = ObjectId(event_id)
    search = (request.args.get("search") or "").strip()

    user_filter = {}
    if search:
        user_filter = {"name": {"$regex": re.escape(search), "$options": "i"}}
        matching_ids = [u["_id"] for u in users_col.find(user_filter, {"_id": 1})]
    else:
        matching_ids = None

    ticket_query = {"event_id": oid, "status": {"$in": ["valid", "checked_in"]}}
    reservation_query = {"event_id": oid, "status": {"$in": ["confirmed", "checked_in"]}}
    if matching_ids is not None:
        ticket_query["user_id"] = {"$in": matching_ids}
        reservation_query["user_id"] = {"$in": matching_ids}

    tickets = list(tickets_col.find(ticket_query))
    reservations = list(table_reservations_col.find(reservation_query))

    all_user_ids = list({d["user_id"] for d in tickets + reservations})
    users = {
        u["_id"]: u for u in users_col.find(
            {"_id": {"$in": all_user_ids}}, {"name": 1, "email": 1, "phone": 1}
        )
    }

    def _guest(doc, kind):
        user = users.get(doc["user_id"], {})
        return {
            "type": kind,
            "id": str(doc["_id"]),
            "name": user.get("name", "Nepoznat"),
            "email": user.get("email"),
            "status": doc["status"],
            "checked_in_at": serialize(doc.get("checked_in_at")),
            "detail": doc.get("ticket_type_name") if kind == "ticket"
                      else f"Stol {doc.get('table_label')}",
        }

    guests = sorted(
        [_guest(t, "ticket") for t in tickets]
        + [_guest(r, "reservation") for r in reservations],
        key=lambda g: g["name"].lower(),
    )
    return jsonify({"guests": guests, "count": len(guests)})


@hostess_bp.route("/checkin/ticket/<ticket_id>", methods=["POST"])
@role_required(*STAFF_ROLES)
def checkin_ticket(ticket_id):
    """Check-in po ID-u karte ili QR kodu (?by=qr)."""
    if request.args.get("by") == "qr":
        query = {"qr_code": ticket_id}
    else:
        query = {"_id": ObjectId(ticket_id)}

    ticket = tickets_col.find_one(query)
    if not ticket:
        return jsonify({"error": "Karta ne postoji"}), 404
    if ticket["status"] == "checked_in":
        return jsonify({"error": "Karta je već iskorištena", "already_used": True}), 409
    if ticket["status"] != "valid":
        return jsonify({"error": f"Karta nije važeća (status: {ticket['status']})"}), 409

    tickets_col.update_one(
        {"_id": ticket["_id"]},
        {"$set": {
            "status": "checked_in",
            "checked_in_at": datetime.utcnow(),
            "checked_in_by": current_user_id(),
        }},
    )
    user = users_col.find_one({"_id": ticket["user_id"]}, {"name": 1})
    return jsonify({
        "success": True,
        "guest_name": (user or {}).get("name"),
        "ticket_type": ticket.get("ticket_type_name"),
    })


@hostess_bp.route("/checkin/reservation/<reservation_id>", methods=["POST"])
@role_required(*STAFF_ROLES)
def checkin_reservation_route(reservation_id):
    try:
        reservation = checkin_reservation(reservation_id, current_user_id())
    except ReservationError as exc:
        return jsonify({"error": str(exc)}), 409

    publish('table_updates', {
        "event_id": str(reservation["event_id"]),
        "table_id": reservation["table_id"],
        "status": "checked_in",
    })
    user = users_col.find_one({"_id": reservation["user_id"]}, {"name": 1})
    return jsonify({
        "success": True,
        "guest_name": (user or {}).get("name"),
        "table_label": reservation.get("table_label"),
    })


@hostess_bp.route("/event/<event_id>/stats", methods=["GET"])
@role_required(*STAFF_ROLES)
def event_stats(event_id):
    """Live statistike ulaska za event."""
    oid = ObjectId(event_id)
    tickets_sold = tickets_col.count_documents(
        {"event_id": oid, "status": {"$in": ["valid", "checked_in"]}}
    )
    tickets_in = tickets_col.count_documents({"event_id": oid, "status": "checked_in"})
    reservations_confirmed = table_reservations_col.count_documents(
        {"event_id": oid, "status": {"$in": ["confirmed", "checked_in"]}}
    )
    reservations_in = table_reservations_col.count_documents(
        {"event_id": oid, "status": "checked_in"}
    )
    return jsonify({
        "event_id": event_id,
        "tickets_sold": tickets_sold,
        "tickets_checked_in": tickets_in,
        "reservations_confirmed": reservations_confirmed,
        "reservations_checked_in": reservations_in,
        "total_inside": tickets_in + reservations_in,
    })
