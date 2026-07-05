"""Eventi — javni feed + admin CRUD."""

import re
from datetime import datetime

from bson import ObjectId
from flask import Blueprint, jsonify, request

from auth_utils import current_club_id, current_role, resolve_club_id, role_required, serialize
from db import clubs_col, events_col

events_bp = Blueprint("events", __name__, url_prefix="/api/events")


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _with_club(event):
    doc = serialize(event)
    club = clubs_col.find_one({"_id": event["club_id"]},
                              {"name": 1, "slug": 1, "location": 1, "cover_image": 1})
    if club:
        doc["club"] = serialize(club)
    return doc


@events_bp.route("", methods=["GET"])
def list_events():
    """Lista objavljenih eventa. Filteri: club_id, city, date_from, date_to."""
    query = {"is_published": True, "is_cancelled": {"$ne": True}}

    club_id = request.args.get("club_id")
    if club_id:
        query["club_id"] = ObjectId(club_id)

    city = request.args.get("city")
    if city:
        club_ids = [
            c["_id"] for c in clubs_col.find(
                {"location.city": {"$regex": f"^{re.escape(city)}$", "$options": "i"}},
                {"_id": 1},
            )
        ]
        query["club_id"] = {"$in": club_ids}

    date_from = _parse_date(request.args.get("date_from"))
    date_to = _parse_date(request.args.get("date_to"))
    if date_from or date_to:
        query["date"] = {}
        if date_from:
            query["date"]["$gte"] = date_from
        if date_to:
            query["date"]["$lte"] = date_to

    events = [_with_club(e) for e in events_col.find(query).sort("date", 1).limit(200)]
    return jsonify({"events": events, "count": len(events)})


@events_bp.route("/upcoming", methods=["GET"])
def upcoming_events():
    """Nadolazeći eventi za home screen."""
    limit = min(int(request.args.get("limit", 20)), 50)
    events = [
        _with_club(e)
        for e in events_col.find({
            "is_published": True,
            "is_cancelled": {"$ne": True},
            "date": {"$gte": datetime.utcnow()},
        }).sort("date", 1).limit(limit)
    ]
    return jsonify({"events": events})


@events_bp.route("/<event_id>", methods=["GET"])
def get_event(event_id):
    event = events_col.find_one({"_id": ObjectId(event_id)})
    if not event:
        return jsonify({"error": "Event ne postoji"}), 404
    return jsonify(_with_club(event))


def _normalize_ticket_types(raw_types):
    """Osigurava id/sold_quantity/is_active na svakom ticket typeu."""
    import uuid
    normalized = []
    for tt in raw_types or []:
        normalized.append({
            "id": tt.get("id") or uuid.uuid4().hex[:8],
            "name": tt.get("name", "Ulaznica"),
            "price": float(tt.get("price", 0)),
            "total_quantity": int(tt.get("total_quantity", 0)),
            "sold_quantity": int(tt.get("sold_quantity", 0)),
            "sale_start": _parse_date(tt.get("sale_start")) if isinstance(tt.get("sale_start"), str) else tt.get("sale_start"),
            "sale_end": _parse_date(tt.get("sale_end")) if isinstance(tt.get("sale_end"), str) else tt.get("sale_end"),
            "description": tt.get("description"),
            "is_active": tt.get("is_active", True),
        })
    return normalized


@events_bp.route("", methods=["POST"])
@role_required("admin", "superadmin")
def create_event():
    data = request.get_json(silent=True) or {}
    club_id = resolve_club_id()
    if not club_id:
        return jsonify({"error": "club_id je obavezan"}), 400

    name = (data.get("name") or "").strip()
    date = _parse_date(data.get("date"))
    if not name or not date:
        return jsonify({"error": "name i date su obavezni"}), 400

    event = {
        "club_id": club_id,
        "name": name,
        "description": data.get("description"),
        "date": date,
        "doors_open": data.get("doors_open"),
        "end_time": data.get("end_time"),
        "genre": data.get("genre"),
        "lineup": data.get("lineup") or [],
        "cover_image": data.get("cover_image"),
        "gallery": data.get("gallery") or [],
        "ticket_types": _normalize_ticket_types(data.get("ticket_types")),
        "age_limit": data.get("age_limit", 18),
        "dress_code": data.get("dress_code"),
        "additional_info": data.get("additional_info"),
        "is_published": data.get("is_published", False),
        "is_cancelled": False,
        "created_at": datetime.utcnow(),
    }
    result = events_col.insert_one(event)
    event["_id"] = result.inserted_id
    return jsonify(serialize(event)), 201


def _can_manage_event(event):
    if current_role() == "superadmin":
        return True
    return current_club_id() == event["club_id"]


@events_bp.route("/<event_id>", methods=["PUT"])
@role_required("admin", "superadmin")
def update_event(event_id):
    event = events_col.find_one({"_id": ObjectId(event_id)})
    if not event:
        return jsonify({"error": "Event ne postoji"}), 404
    if not _can_manage_event(event):
        return jsonify({"error": "Nemate ovlasti nad ovim eventom"}), 403

    data = request.get_json(silent=True) or {}
    allowed = [
        "name", "description", "doors_open", "end_time", "genre", "lineup",
        "cover_image", "gallery", "age_limit", "dress_code",
        "additional_info", "is_published",
    ]
    updates = {k: data[k] for k in allowed if k in data}
    if "date" in data:
        parsed = _parse_date(data["date"])
        if parsed:
            updates["date"] = parsed
    if "ticket_types" in data:
        updates["ticket_types"] = _normalize_ticket_types(data["ticket_types"])
    if not updates:
        return jsonify({"error": "Nema podataka za ažuriranje"}), 400

    result = events_col.find_one_and_update(
        {"_id": event["_id"]}, {"$set": updates}, return_document=True
    )
    return jsonify(serialize(result))


@events_bp.route("/<event_id>", methods=["DELETE"])
@role_required("admin", "superadmin")
def cancel_event(event_id):
    """Otkazivanje eventa (soft delete — karte ostaju radi refunda)."""
    event = events_col.find_one({"_id": ObjectId(event_id)})
    if not event:
        return jsonify({"error": "Event ne postoji"}), 404
    if not _can_manage_event(event):
        return jsonify({"error": "Nemate ovlasti nad ovim eventom"}), 403

    events_col.update_one(
        {"_id": event["_id"]},
        {"$set": {"is_cancelled": True, "is_published": False}},
    )
    return jsonify({"success": True, "message": "Event je otkazan"})
