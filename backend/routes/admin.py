"""Admin panel — dashboard, live prikaz eventa, izvještaji, upravljanje osobljem."""

import re
from datetime import datetime, timedelta

from bson import ObjectId
from flask import Blueprint, jsonify, request
from pymongo.errors import DuplicateKeyError

from auth_utils import (
    current_club_id, current_role, hash_password, resolve_club_id,
    role_required, serialize,
)
from db import (
    club_admins_col, drink_orders_col, events_col, hostesses_col, reports_col,
    superadmins_col, table_reservations_col, tickets_col, users_col, waiters_col,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _club_or_403():
    club_id = resolve_club_id()
    if not club_id:
        return None, (jsonify({"error": "club_id nije određen"}), 400)
    return club_id, None


def _sum_and_count(col, match, field):
    """Zbroj polja + broj dokumenata kroz Mongo agregaciju (bez vučenja u Python)."""
    res = list(col.aggregate([
        {"$match": match},
        {"$group": {"_id": None, "total": {"$sum": f"${field}"}, "count": {"$sum": 1}}},
    ]))
    if not res:
        return 0.0, 0
    return round(res[0]["total"] or 0, 2), res[0]["count"]


@admin_bp.route("/dashboard", methods=["GET"])
@role_required("admin", "superadmin")
def dashboard():
    """Sumarne statistike kluba (zadnjih 30 dana + nadolazeće)."""
    club_id, err = _club_or_403()
    if err:
        return err

    now = datetime.utcnow()
    month_ago = now - timedelta(days=30)

    revenue_tickets, tickets_sold = _sum_and_count(tickets_col, {
        "club_id": club_id,
        "purchased_at": {"$gte": month_ago},
        "status": {"$in": ["valid", "checked_in"]},
    }, "price_paid")

    revenue_drinks, drink_orders = _sum_and_count(drink_orders_col, {
        "club_id": club_id,
        "created_at": {"$gte": month_ago},
        "payment_status": "paid",
    }, "total")

    revenue_deposits, _ = _sum_and_count(table_reservations_col, {
        "club_id": club_id,
        "created_at": {"$gte": month_ago},
        "deposit_paid": True,
    }, "deposit_amount")

    upcoming_events = events_col.count_documents({
        "club_id": club_id,
        "is_cancelled": {"$ne": True},
        "date": {"$gte": now},
    })

    return jsonify({
        "period_days": 30,
        "upcoming_events": upcoming_events,
        "tickets_sold": tickets_sold,
        "reservations": table_reservations_col.count_documents({
            "club_id": club_id, "created_at": {"$gte": month_ago},
        }),
        "drink_orders": drink_orders,
        "revenue_tickets": revenue_tickets,
        "revenue_drinks": revenue_drinks,
        "revenue_deposits": revenue_deposits,
        "total_revenue": round(revenue_tickets + revenue_drinks + revenue_deposits, 2),
    })


@admin_bp.route("/events/<event_id>/live", methods=["GET"])
@role_required("admin", "superadmin")
def live_dashboard(event_id):
    """Live prikaz eventa — ulasci, rezervacije, narudžbe u tijeku."""
    event = events_col.find_one({"_id": ObjectId(event_id)})
    if not event:
        return jsonify({"error": "Event ne postoji"}), 404
    if current_role() != "superadmin" and current_club_id() != event["club_id"]:
        return jsonify({"error": "Nemate ovlasti nad ovim eventom"}), 403

    oid = event["_id"]
    tickets_sold = tickets_col.count_documents(
        {"event_id": oid, "status": {"$in": ["valid", "checked_in"]}}
    )
    checked_in = tickets_col.count_documents({"event_id": oid, "status": "checked_in"})
    reservations_active = table_reservations_col.count_documents(
        {"event_id": oid, "status": {"$in": ["confirmed", "checked_in"]}}
    )
    reservations_in = table_reservations_col.count_documents(
        {"event_id": oid, "status": "checked_in"}
    )
    active_orders = drink_orders_col.count_documents(
        {"event_id": oid, "order_status": {"$in": ["placed", "accepted", "preparing"]}}
    )
    drink_revenue = list(drink_orders_col.aggregate([
        {"$match": {"event_id": oid, "payment_status": "paid"}},
        {"$group": {"_id": None, "total": {"$sum": "$total"}}},
    ]))

    return jsonify({
        "event": {"id": str(oid), "name": event["name"], "date": serialize(event["date"])},
        "tickets_sold": tickets_sold,
        "tickets_checked_in": checked_in,
        "reservations_active": reservations_active,
        "reservations_checked_in": reservations_in,
        "guests_inside": checked_in + reservations_in,
        "active_drink_orders": active_orders,
        "drink_revenue": round((drink_revenue[0]["total"] if drink_revenue else 0), 2),
    })


@admin_bp.route("/reports", methods=["GET"])
@role_required("admin", "superadmin")
def reports():
    club_id, err = _club_or_403()
    if err:
        return err
    limit = min(int(request.args.get("limit", 30)), 100)
    docs = [
        serialize(r) for r in reports_col.find({"club_id": club_id})
        .sort("date", -1).limit(limit)
    ]
    return jsonify({"reports": docs})


STAFF_COLLECTIONS = {
    "hostess": hostesses_col,
    "waiter": waiters_col,
}


@admin_bp.route("/staff", methods=["POST"])
@role_required("admin", "superadmin")
def add_staff():
    """Dodavanje hostese ili konobara (email + PIN prijava)."""
    club_id, err = _club_or_403()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    role = data.get("role")
    if role not in STAFF_COLLECTIONS:
        return jsonify({"error": "role mora biti 'hostess' ili 'waiter'"}), 400

    email = (data.get("email") or "").strip().lower()
    name = (data.get("name") or "").strip()
    pin = str(data.get("pin") or "")
    if not email or not name:
        return jsonify({"error": "name i email su obavezni"}), 400
    if not (pin.isdigit() and len(pin) == 4):
        return jsonify({"error": "PIN mora biti 4 znamenke"}), 400

    col = STAFF_COLLECTIONS[role]
    if hostesses_col.find_one({"email": email}) or waiters_col.find_one({"email": email}):
        return jsonify({"error": "Osoblje s tim emailom već postoji"}), 409

    staff = {
        "club_id": club_id,
        "name": name,
        "email": email,
        "pin_hash": hash_password(pin),
        "password_hash": hash_password(data["password"]) if data.get("password") else None,
        "role": role,
        "is_active": True,
        "created_at": datetime.utcnow(),
    }
    if role == "waiter":
        staff["assigned_sections"] = data.get("assigned_sections") or []

    result = col.insert_one(staff)
    staff["_id"] = result.inserted_id
    doc = serialize(staff)
    doc.pop("password_hash", None)
    doc.pop("pin_hash", None)
    return jsonify(doc), 201


@admin_bp.route("/staff/<staff_id>/sections", methods=["PUT"])
@role_required("admin", "superadmin")
def assign_sections(staff_id):
    """Dodjela sekcija tlocrta konobaru."""
    club_id, err = _club_or_403()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    sections = data.get("sections")
    if not isinstance(sections, list):
        return jsonify({"error": "sections mora biti lista section id-eva"}), 400

    result = waiters_col.find_one_and_update(
        {"_id": ObjectId(staff_id), "club_id": club_id},
        {"$set": {"assigned_sections": sections}},
        return_document=True,
    )
    if not result:
        return jsonify({"error": "Konobar ne postoji u ovom klubu"}), 404
    doc = serialize(result)
    doc.pop("password_hash", None)
    doc.pop("pin", None)
    doc.pop("pin_hash", None)
    return jsonify(doc)


@admin_bp.route("/staff", methods=["GET"])
@role_required("admin", "superadmin")
def list_staff():
    club_id, err = _club_or_403()
    if err:
        return err

    def _clean(doc, role):
        d = serialize(doc)
        d.pop("password_hash", None)
        d.pop("pin", None)
        d.pop("pin_hash", None)
        d["role"] = role
        return d

    staff = (
        [_clean(h, "hostess") for h in hostesses_col.find({"club_id": club_id})]
        + [_clean(w, "waiter") for w in waiters_col.find({"club_id": club_id})]
    )
    return jsonify({"staff": staff, "count": len(staff)})


@admin_bp.route("/club-admins", methods=["POST"])
@role_required("superadmin")
def add_club_admin():
    """Kreiranje admina kluba — samo superadmin."""
    club_id, err = _club_or_403()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    name = (data.get("name") or "").strip()
    password = data.get("password") or ""

    if not email or "@" not in email:
        return jsonify({"error": "Neispravan email"}), 400
    if not name:
        return jsonify({"error": "Ime je obavezno"}), 400
    if len(password) < 6:
        return jsonify({"error": "Lozinka mora imati barem 6 znakova"}), 400

    admin_doc = {
        "club_id": club_id,
        "name": name,
        "email": email,
        "password_hash": hash_password(password),
        "is_active": True,
        "created_at": datetime.utcnow(),
    }
    try:
        result = club_admins_col.insert_one(admin_doc)
    except DuplicateKeyError:
        return jsonify({"error": "Admin s tim emailom već postoji"}), 409

    admin_doc["_id"] = result.inserted_id
    doc = serialize(admin_doc)
    doc.pop("password_hash", None)
    return jsonify(doc), 201


@admin_bp.route("/club-admins", methods=["GET"])
@role_required("superadmin")
def list_club_admins():
    """Popis admina za odabrani klub — samo superadmin."""
    club_id, err = _club_or_403()
    if err:
        return err

    admins = []
    for a in club_admins_col.find({"club_id": club_id}):
        doc = serialize(a)
        doc.pop("password_hash", None)
        admins.append(doc)
    return jsonify({"admins": admins})


@admin_bp.route("/superadmins", methods=["POST"])
@role_required("superadmin")
def add_superadmin():
    """Kreiranje dodatnog superadmina — samo superadmin."""
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""

    if not username:
        return jsonify({"error": "Korisničko ime je obavezno"}), 400
    if len(password) < 6:
        return jsonify({"error": "Lozinka mora imati barem 6 znakova"}), 400

    doc = {
        "username": username,
        "password_hash": hash_password(password),
        "role": "superadmin",
        "created_at": datetime.utcnow(),
    }
    try:
        result = superadmins_col.insert_one(doc)
    except DuplicateKeyError:
        return jsonify({"error": "Superadmin s tim korisničkim imenom već postoji"}), 409

    doc["_id"] = result.inserted_id
    out = serialize(doc)
    out.pop("password_hash", None)
    return jsonify(out), 201


@admin_bp.route("/superadmins", methods=["GET"])
@role_required("superadmin")
def list_superadmins():
    """Popis svih superadmina."""
    admins = []
    for a in superadmins_col.find({}):
        doc = serialize(a)
        doc.pop("password_hash", None)
        admins.append(doc)
    return jsonify({"admins": admins})


@admin_bp.route("/users", methods=["POST"])
@role_required("superadmin")
def add_guest_user():
    """Kreiranje gostinjskog računa — samo superadmin (gost se inače sam registrira)."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    name = (data.get("name") or "").strip()
    password = data.get("password") or ""
    phone = data.get("phone")

    if not email or "@" not in email:
        return jsonify({"error": "Neispravan email"}), 400
    if not name:
        return jsonify({"error": "Ime je obavezno"}), 400
    if len(password) < 6:
        return jsonify({"error": "Lozinka mora imati barem 6 znakova"}), 400

    user = {
        "email": email,
        "name": name,
        "phone": phone,
        "profile_image": None,
        "auth_provider": "email",
        "auth_provider_id": None,
        "password_hash": hash_password(password),
        "stripe_customer_id": None,
        "is_active": True,
        "created_at": datetime.utcnow(),
    }
    try:
        result = users_col.insert_one(user)
    except DuplicateKeyError:
        return jsonify({"error": "Korisnik s tim emailom već postoji"}), 409

    user["_id"] = result.inserted_id
    doc = serialize(user)
    doc.pop("password_hash", None)
    return jsonify(doc), 201


@admin_bp.route("/users", methods=["GET"])
@role_required("superadmin")
def list_guest_users():
    """Popis gostiju (najnoviji prvi), opcionalni ?search= po imenu/emailu."""
    query = {}
    search = (request.args.get("search") or "").strip()
    if search:
        escaped = re.escape(search)
        query["$or"] = [
            {"name": {"$regex": escaped, "$options": "i"}},
            {"email": {"$regex": escaped, "$options": "i"}},
        ]
    limit = min(int(request.args.get("limit", 50)), 200)
    users = []
    for u in users_col.find(query).sort("created_at", -1).limit(limit):
        doc = serialize(u)
        doc.pop("password_hash", None)
        users.append(doc)
    return jsonify({"users": users})
