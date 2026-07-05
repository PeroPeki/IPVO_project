"""Mape stolova — javni prikaz s dostupnošću + admin editor (drag & drop)."""

from datetime import datetime

from bson import ObjectId
from flask import Blueprint, jsonify, request

from auth_utils import current_club_id, current_role, resolve_club_id, role_required, serialize
from db import events_col, floor_maps_col, table_reservations_col
from reservation_service import ACTIVE_STATUSES
from upload_service import save_image

floor_maps_bp = Blueprint("floor_maps", __name__, url_prefix="/api/floor-maps")


@floor_maps_bp.route("/club/<club_id>", methods=["GET"])
def club_floor_map(club_id):
    floor_map = floor_maps_col.find_one(
        {"club_id": ObjectId(club_id), "is_active": True}
    )
    if not floor_map:
        return jsonify({"error": "Klub nema aktivnu mapu stolova"}), 404
    return jsonify(serialize(floor_map))


@floor_maps_bp.route("/event/<event_id>", methods=["GET"])
def event_floor_map(event_id):
    """Mapa kluba + statusi stolova za konkretni event (za SVG prikaz)."""
    event = events_col.find_one({"_id": ObjectId(event_id)})
    if not event:
        return jsonify({"error": "Event ne postoji"}), 404

    floor_map = floor_maps_col.find_one(
        {"club_id": event["club_id"], "is_active": True}
    )
    if not floor_map:
        return jsonify({"error": "Klub nema aktivnu mapu stolova"}), 404

    reservations = table_reservations_col.find(
        {"event_id": event["_id"], "status": {"$in": ACTIVE_STATUSES}},
        {"table_id": 1, "status": 1},
    )
    status_by_table = {r["table_id"]: r["status"] for r in reservations}

    doc = serialize(floor_map)
    for table in doc.get("tables", []):
        table["reservation_status"] = status_by_table.get(table["id"])
        table["is_available"] = table["id"] not in status_by_table
    return jsonify(doc)


def _can_manage(club_id):
    return current_role() == "superadmin" or current_club_id() == club_id


@floor_maps_bp.route("", methods=["POST"])
@role_required("admin", "superadmin")
def create_floor_map():
    data = request.get_json(silent=True) or {}
    club_id = resolve_club_id()
    if not club_id:
        return jsonify({"error": "club_id je obavezan"}), 400

    floor_map = {
        "club_id": club_id,
        "name": data.get("name", "Glavni tlocrt"),
        "background_image_url": data.get("background_image_url"),
        "width": int(data.get("width", 1000)),
        "height": int(data.get("height", 700)),
        "tables": data.get("tables") or [],
        "sections": data.get("sections") or [],
        "is_active": data.get("is_active", True),
        "updated_at": datetime.utcnow(),
    }
    # Jedan klub, jedna aktivna mapa — deaktiviraj prethodne
    if floor_map["is_active"]:
        floor_maps_col.update_many(
            {"club_id": club_id}, {"$set": {"is_active": False}}
        )
    result = floor_maps_col.insert_one(floor_map)
    floor_map["_id"] = result.inserted_id
    return jsonify(serialize(floor_map)), 201


def _get_managed_map(map_id):
    floor_map = floor_maps_col.find_one({"_id": ObjectId(map_id)})
    if not floor_map:
        return None, (jsonify({"error": "Mapa ne postoji"}), 404)
    if not _can_manage(floor_map["club_id"]):
        return None, (jsonify({"error": "Nemate ovlasti nad ovom mapom"}), 403)
    return floor_map, None


@floor_maps_bp.route("/<map_id>", methods=["PUT"])
@role_required("admin", "superadmin")
def update_floor_map(map_id):
    floor_map, err = _get_managed_map(map_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    allowed = ["name", "background_image_url", "width", "height",
               "tables", "sections", "is_active"]
    updates = {k: data[k] for k in allowed if k in data}
    updates["updated_at"] = datetime.utcnow()

    result = floor_maps_col.find_one_and_update(
        {"_id": floor_map["_id"]}, {"$set": updates}, return_document=True
    )
    return jsonify(serialize(result))


@floor_maps_bp.route("/<map_id>/upload-bg", methods=["POST"])
@role_required("admin", "superadmin")
def upload_background(map_id):
    floor_map, err = _get_managed_map(map_id)
    if err:
        return err
    if "image" not in request.files:
        return jsonify({"error": "Datoteka 'image' je obavezna"}), 400

    try:
        url = save_image(request.files["image"], folder="floor-maps")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    floor_maps_col.update_one(
        {"_id": floor_map["_id"]},
        {"$set": {"background_image_url": url, "updated_at": datetime.utcnow()}},
    )
    return jsonify({"url": url}), 201


@floor_maps_bp.route("/<map_id>/tables", methods=["PUT"])
@role_required("admin", "superadmin")
def update_tables(map_id):
    """Sprema raspored stolova i sekcija iz admin editora (drag & drop)."""
    floor_map, err = _get_managed_map(map_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    updates = {"updated_at": datetime.utcnow()}
    if "tables" in data:
        updates["tables"] = data["tables"]
    if "sections" in data:
        updates["sections"] = data["sections"]

    result = floor_maps_col.find_one_and_update(
        {"_id": floor_map["_id"]}, {"$set": updates}, return_document=True
    )
    return jsonify(serialize(result))
