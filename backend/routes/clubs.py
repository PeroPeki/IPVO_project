"""Klubovi — javni pregled + administracija (superadmin kreira, admin uređuje)."""

import re
import unicodedata
from datetime import datetime

from bson import ObjectId
from flask import Blueprint, jsonify, request

from auth_utils import current_club_id, current_role, role_required, serialize
from db import clubs_col
from upload_service import save_image

clubs_bp = Blueprint("clubs", __name__, url_prefix="/api/clubs")


def slugify(text):
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "klub"


@clubs_bp.route("", methods=["GET"])
def list_clubs():
    """Lista aktivnih klubova, opcionalni filter ?city=."""
    query = {"is_active": True}
    city = request.args.get("city")
    if city:
        query["location.city"] = {"$regex": f"^{re.escape(city)}$", "$options": "i"}

    pipeline = [
        {"$match": query},
        {"$lookup": {
            "from": "events",
            "let": {"cid": "$_id"},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$club_id", "$$cid"]},
                            "is_published": True, "is_cancelled": {"$ne": True},
                            "date": {"$gte": datetime.utcnow()}}},
            ],
            "as": "_upcoming",
        }},
        {"$addFields": {"upcoming_event_count": {"$size": "$_upcoming"}}},
        {"$project": {"_upcoming": 0}},
        {"$sort": {"name": 1}},
    ]
    clubs = [serialize(c) for c in clubs_col.aggregate(pipeline)]
    return jsonify({"clubs": clubs})


@clubs_bp.route("/<slug>", methods=["GET"])
def get_club(slug):
    club = clubs_col.find_one({"slug": slug, "is_active": True})
    if not club:
        return jsonify({"error": "Klub ne postoji"}), 404
    return jsonify(serialize(club))


@clubs_bp.route("", methods=["POST"])
@role_required("superadmin")
def create_club():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Naziv kluba je obavezan"}), 400

    slug = data.get("slug") or slugify(name)
    if clubs_col.find_one({"slug": slug}):
        return jsonify({"error": f"Slug '{slug}' je zauzet"}), 409

    club = {
        "name": name,
        "slug": slug,
        "location": {
            "city": (data.get("location") or {}).get("city") or data.get("city"),
            "address": (data.get("location") or {}).get("address") or data.get("address"),
            "coordinates": (data.get("location") or {}).get("coordinates")
                            or {"lat": 0.0, "lng": 0.0},
        },
        "description": data.get("description"),
        "capacity": data.get("capacity"),
        "cover_image": data.get("cover_image"),
        "gallery": data.get("gallery") or [],
        "social_links": data.get("social_links") or {},
        "working_hours": data.get("working_hours"),
        "dress_code": data.get("dress_code"),
        "age_limit": data.get("age_limit", 18),
        "amenities": data.get("amenities") or [],
        "admin_id": ObjectId(data["admin_id"]) if data.get("admin_id") else None,
        "is_active": data.get("is_active", True),
        "created_at": datetime.utcnow(),
    }
    result = clubs_col.insert_one(club)
    club["_id"] = result.inserted_id
    return jsonify(serialize(club)), 201


def _can_manage_club(club_id):
    if current_role() == "superadmin":
        return True
    return current_club_id() == club_id


@clubs_bp.route("/<club_id>", methods=["PUT"])
@role_required("admin", "superadmin")
def update_club(club_id):
    oid = ObjectId(club_id)
    if not _can_manage_club(oid):
        return jsonify({"error": "Nemate ovlasti nad ovim klubom"}), 403

    data = request.get_json(silent=True) or {}
    allowed = [
        "name", "description", "capacity", "cover_image", "gallery",
        "social_links", "working_hours", "dress_code", "age_limit",
        "amenities", "location", "is_active",
    ]
    updates = {k: data[k] for k in allowed if k in data}
    if not updates:
        return jsonify({"error": "Nema podataka za ažuriranje"}), 400

    result = clubs_col.find_one_and_update(
        {"_id": oid}, {"$set": updates}, return_document=True
    )
    if not result:
        return jsonify({"error": "Klub ne postoji"}), 404
    return jsonify(serialize(result))


@clubs_bp.route("/<club_id>/upload-image", methods=["POST"])
@role_required("admin", "superadmin")
def upload_club_image(club_id):
    """Upload slike kluba. ?field=cover (default) ili ?field=gallery."""
    oid = ObjectId(club_id)
    if not _can_manage_club(oid):
        return jsonify({"error": "Nemate ovlasti nad ovim klubom"}), 403
    if "image" not in request.files:
        return jsonify({"error": "Datoteka 'image' je obavezna"}), 400

    try:
        url = save_image(request.files["image"], folder="clubs")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    field = request.args.get("field", "cover")
    if field == "gallery":
        clubs_col.update_one({"_id": oid}, {"$push": {"gallery": url}})
    else:
        clubs_col.update_one({"_id": oid}, {"$set": {"cover_image": url}})
    return jsonify({"url": url}), 201
