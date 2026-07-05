"""Meni pića — javni prikaz + admin CRUD."""

import uuid
from datetime import datetime

from bson import ObjectId
from flask import Blueprint, jsonify, request

from auth_utils import current_club_id, current_role, resolve_club_id, role_required, serialize
from db import menus_col

menu_bp = Blueprint("menu", __name__, url_prefix="/api/menu")


def _normalize_categories(raw_categories):
    """Osigurava id-eve na kategorijama i stavkama."""
    categories = []
    for cat in raw_categories or []:
        items = []
        for item in cat.get("items", []):
            items.append({
                "id": item.get("id") or uuid.uuid4().hex[:8],
                "name": item.get("name", ""),
                "description": item.get("description"),
                "price": float(item.get("price", 0)),
                "image_url": item.get("image_url"),
                "is_available": item.get("is_available", True),
                "allergens": item.get("allergens") or [],
                "volume": item.get("volume"),
            })
        categories.append({
            "id": cat.get("id") or uuid.uuid4().hex[:8],
            "name": cat.get("name", ""),
            "items": items,
        })
    return categories


@menu_bp.route("/club/<club_id>", methods=["GET"])
def club_menu(club_id):
    menu = menus_col.find_one({"club_id": ObjectId(club_id), "is_active": True})
    if not menu:
        return jsonify({"error": "Klub nema aktivan meni"}), 404
    return jsonify(serialize(menu))


def _can_manage(club_id):
    return current_role() == "superadmin" or current_club_id() == club_id


@menu_bp.route("", methods=["POST"])
@role_required("admin", "superadmin")
def create_menu():
    data = request.get_json(silent=True) or {}
    club_id = resolve_club_id()
    if not club_id:
        return jsonify({"error": "club_id je obavezan"}), 400

    menu = {
        "club_id": club_id,
        "name": data.get("name", "Cjenik pića"),
        "categories": _normalize_categories(data.get("categories")),
        "is_active": data.get("is_active", True),
        "updated_at": datetime.utcnow(),
    }
    if menu["is_active"]:
        menus_col.update_many({"club_id": club_id}, {"$set": {"is_active": False}})
    result = menus_col.insert_one(menu)
    menu["_id"] = result.inserted_id
    return jsonify(serialize(menu)), 201


@menu_bp.route("/<menu_id>", methods=["PUT"])
@role_required("admin", "superadmin")
def update_menu(menu_id):
    menu = menus_col.find_one({"_id": ObjectId(menu_id)})
    if not menu:
        return jsonify({"error": "Meni ne postoji"}), 404
    if not _can_manage(menu["club_id"]):
        return jsonify({"error": "Nemate ovlasti nad ovim menijem"}), 403

    data = request.get_json(silent=True) or {}
    updates = {"updated_at": datetime.utcnow()}
    if "name" in data:
        updates["name"] = data["name"]
    if "is_active" in data:
        updates["is_active"] = data["is_active"]
    if "categories" in data:
        updates["categories"] = _normalize_categories(data["categories"])

    result = menus_col.find_one_and_update(
        {"_id": menu["_id"]}, {"$set": updates}, return_document=True
    )
    return jsonify(serialize(result))


@menu_bp.route("/<menu_id>/item/<item_id>/availability", methods=["PATCH"])
@role_required("admin", "superadmin")
def toggle_item_availability(menu_id, item_id):
    """Brzo pali/gasi dostupnost pojedine stavke (npr. ponestalo pića)."""
    menu = menus_col.find_one({"_id": ObjectId(menu_id)})
    if not menu:
        return jsonify({"error": "Meni ne postoji"}), 404
    if not _can_manage(menu["club_id"]):
        return jsonify({"error": "Nemate ovlasti nad ovim menijem"}), 403

    data = request.get_json(silent=True) or {}
    is_available = bool(data.get("is_available", True))

    result = menus_col.update_one(
        {"_id": menu["_id"]},
        {"$set": {
            "categories.$[].items.$[i].is_available": is_available,
            "updated_at": datetime.utcnow(),
        }},
        array_filters=[{"i.id": item_id}],
    )
    if result.modified_count == 0:
        return jsonify({"error": "Stavka ne postoji ili je već u tom stanju"}), 404
    return jsonify({"success": True, "item_id": item_id, "is_available": is_available})
