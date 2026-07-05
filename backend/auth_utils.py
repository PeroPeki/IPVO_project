"""
Pomoćni alati za autentikaciju i autorizaciju (JWT + role).

Role u sustavu: user, admin, superadmin, hostess, waiter.
JWT identity je string ObjectId-a, a dodatni claimovi nose `role`
i (za osoblje/admine) `club_id`.
"""

from datetime import datetime
from functools import wraps

from bson import ObjectId
from flask import jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    verify_jwt_in_request,
)
from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(password):
    return generate_password_hash(password)


def verify_password(password_hash, password):
    if not password_hash:
        return False
    return check_password_hash(password_hash, password)


def issue_tokens(identity, role, club_id=None):
    """Vraća access + refresh token s role/club_id claimovima."""
    claims = {"role": role}
    if club_id is not None:
        claims["club_id"] = str(club_id)
    return {
        "access_token": create_access_token(identity=str(identity), additional_claims=claims),
        "refresh_token": create_refresh_token(identity=str(identity), additional_claims=claims),
    }


def role_required(*roles):
    """Dekorator: dopušta pristup samo navedenim rolama."""

    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get("role") not in roles:
                return jsonify({"error": "Nedovoljne ovlasti"}), 403
            return fn(*args, **kwargs)

        return decorator

    return wrapper


def current_user_id():
    """ObjectId trenutno prijavljenog subjekta (bilo koje role)."""
    return ObjectId(get_jwt_identity())


def current_role():
    return get_jwt().get("role")


def current_club_id():
    """ObjectId kluba iz claimova (admin/hostess/waiter) ili None."""
    club_id = get_jwt().get("club_id")
    return ObjectId(club_id) if club_id else None


def resolve_club_id():
    """
    Klub nad kojim admin operira: club admin je vezan claimom,
    superadmin smije birati putem ?club_id= ili body polja.
    """
    club_id = current_club_id()
    if club_id:
        return club_id
    raw = request.args.get("club_id")
    if not raw and request.is_json:
        raw = (request.get_json(silent=True) or {}).get("club_id")
    return ObjectId(raw) if raw else None


def serialize(value):
    """Rekurzivno pretvara ObjectId i datetime u JSON-serializabilne tipove."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: serialize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [serialize(v) for v in value]
    return value
