"""Autentikacija — registracija, prijava (user/admin/staff), OAuth, refresh, logout."""

from datetime import datetime

import requests as ext_requests
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from auth_utils import hash_password, issue_tokens, serialize, verify_password
from db import club_admins_col, hostesses_col, superadmins_col, users_col, waiters_col
from extensions import limiter, redis_client

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _public_user(user):
    doc = serialize(user)
    doc.pop("password_hash", None)
    doc.pop("pin", None)
    doc.pop("pin_hash", None)
    return doc


def _revoke_current_token():
    """Dodaje jti predanog tokena na blocklist do njegova isteka."""
    payload = get_jwt()
    ttl = payload["exp"] - int(datetime.utcnow().timestamp())
    if ttl > 0:
        try:
            redis_client.setex(f"revoked_jwt:{payload['jti']}", ttl, "1")
        except Exception as exc:
            print(f"[auth] Revokacija tokena nije uspjela: {exc}")


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("30 per hour")
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip()

    if not email or "@" not in email:
        return jsonify({"error": "Neispravan email"}), 400
    if len(password) < 6:
        return jsonify({"error": "Lozinka mora imati barem 6 znakova"}), 400
    if not name:
        return jsonify({"error": "Ime je obavezno"}), 400
    if users_col.find_one({"email": email}):
        return jsonify({"error": "Korisnik s tim emailom već postoji"}), 409

    user = {
        "email": email,
        "name": name,
        "phone": data.get("phone"),
        "profile_image": None,
        "auth_provider": "email",
        "auth_provider_id": None,
        "password_hash": hash_password(password),
        "stripe_customer_id": None,
        "is_active": True,
        "created_at": datetime.utcnow(),
    }
    result = users_col.insert_one(user)
    user["_id"] = result.inserted_id

    tokens = issue_tokens(result.inserted_id, "user")
    return jsonify({**tokens, "user": _public_user(user)}), 201


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = users_col.find_one({"email": email, "is_active": True})
    if not user or not verify_password(user.get("password_hash"), password):
        return jsonify({"error": "Neispravan email ili lozinka"}), 401

    tokens = issue_tokens(user["_id"], "user")
    return jsonify({**tokens, "user": _public_user(user)})


def _oauth_upsert(email, name, provider, provider_id, picture=None):
    """Nađi ili kreiraj korisnika iz OAuth podataka i izdaj tokene."""
    user = users_col.find_one({"email": email})
    if not user:
        user = {
            "email": email,
            "name": name or email.split("@")[0],
            "phone": None,
            "profile_image": picture,
            "auth_provider": provider,
            "auth_provider_id": provider_id,
            "password_hash": None,
            "stripe_customer_id": None,
            "is_active": True,
            "created_at": datetime.utcnow(),
        }
        user["_id"] = users_col.insert_one(user).inserted_id
    else:
        users_col.update_one(
            {"_id": user["_id"]},
            {"$set": {"auth_provider": provider, "auth_provider_id": provider_id}},
        )
    tokens = issue_tokens(user["_id"], "user")
    return jsonify({**tokens, "user": _public_user(user)})


@auth_bp.route("/google", methods=["POST"])
@limiter.limit("10 per minute")
def google_auth():
    """Prima {id_token} iz Expo Google auth sessiona i verificira ga kod Googlea."""
    data = request.get_json(silent=True) or {}
    id_token = data.get("id_token")
    if not id_token:
        return jsonify({"error": "id_token je obavezan"}), 400
    try:
        resp = ext_requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
            timeout=10,
        )
        if resp.status_code != 200:
            return jsonify({"error": "Neispravan Google token"}), 401
        info = resp.json()
        return _oauth_upsert(
            info["email"].lower(), info.get("name"), "google",
            info.get("sub"), info.get("picture"),
        )
    except Exception as exc:
        return jsonify({"error": f"Google verifikacija nije uspjela: {exc}"}), 502


@auth_bp.route("/facebook", methods=["POST"])
@limiter.limit("10 per minute")
def facebook_auth():
    """Prima {access_token} i verificira ga na Facebook Graph API-ju."""
    data = request.get_json(silent=True) or {}
    access_token = data.get("access_token")
    if not access_token:
        return jsonify({"error": "access_token je obavezan"}), 400
    try:
        resp = ext_requests.get(
            "https://graph.facebook.com/me",
            params={"fields": "id,name,email,picture", "access_token": access_token},
            timeout=10,
        )
        if resp.status_code != 200:
            return jsonify({"error": "Neispravan Facebook token"}), 401
        info = resp.json()
        email = (info.get("email") or f"fb_{info['id']}@facebook.local").lower()
        picture = ((info.get("picture") or {}).get("data") or {}).get("url")
        return _oauth_upsert(email, info.get("name"), "facebook", info["id"], picture)
    except Exception as exc:
        return jsonify({"error": f"Facebook verifikacija nije uspjela: {exc}"}), 502


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    claims = get_jwt()
    tokens = issue_tokens(
        get_jwt_identity(), claims.get("role", "user"), claims.get("club_id")
    )
    # Rotacija: iskorišteni refresh token više ne vrijedi
    _revoke_current_token()
    return jsonify(tokens)


@auth_bp.route("/logout", methods=["POST"])
@jwt_required(verify_type=False)
def logout():
    """Revocira predani token (access ili refresh). Klijent šalje oba redom."""
    _revoke_current_token()
    return jsonify({"success": True})


@auth_bp.route("/admin/login", methods=["POST"])
@limiter.limit("10 per minute")
def admin_login():
    """Prijava club admina (email) ili superadmina (username)."""
    data = request.get_json(silent=True) or {}
    identifier = (data.get("email") or data.get("username") or "").strip().lower()
    password = data.get("password") or ""

    admin = club_admins_col.find_one({"email": identifier})
    if admin and verify_password(admin.get("password_hash"), password):
        tokens = issue_tokens(admin["_id"], "admin", admin["club_id"])
        return jsonify({**tokens, "admin": _public_user(admin), "role": "admin"})

    superadmin = superadmins_col.find_one({"username": identifier})
    if superadmin and verify_password(superadmin.get("password_hash"), password):
        tokens = issue_tokens(superadmin["_id"], "superadmin")
        return jsonify({**tokens, "admin": _public_user(superadmin), "role": "superadmin"})

    return jsonify({"error": "Neispravni pristupni podaci"}), 401


@auth_bp.route("/staff/login", methods=["POST"])
@limiter.limit("5 per minute; 30 per hour")
def staff_login():
    """Prijava hostese/konobara — email + 4-znamenkasti PIN (brzo na tabletu)."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    pin = str(data.get("pin") or "")

    for col, role in ((hostesses_col, "hostess"), (waiters_col, "waiter")):
        staff = col.find_one({"email": email, "is_active": True})
        if not staff:
            continue

        ok = False
        if staff.get("pin_hash"):
            ok = verify_password(staff["pin_hash"], pin)
        elif staff.get("pin") is not None:
            # Naslijeđeni zapisi s PIN-om u čistom tekstu — hashiraj pri prvoj prijavi
            ok = str(staff["pin"]) == pin
            if ok:
                col.update_one(
                    {"_id": staff["_id"]},
                    {"$set": {"pin_hash": hash_password(pin)}, "$unset": {"pin": ""}},
                )

        if ok:
            tokens = issue_tokens(staff["_id"], role, staff["club_id"])
            return jsonify({**tokens, "staff": _public_user(staff), "role": role})

    return jsonify({"error": "Neispravan email ili PIN"}), 401
