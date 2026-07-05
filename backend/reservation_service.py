"""
Logika rezervacija stolova s depozitom (FAZA 6).

VIP separé zahtijeva depozit koji se nakon plaćanja pretvara u kupon
(`deposit_coupon_remaining`) potrošiv na narudžbe pića. Atomnost drži
partial unique indeks na (event_id, table_id) uz active_hold=True.
"""

from datetime import datetime, timedelta

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

import stripe_service
from db import events_col, floor_maps_col, table_reservations_col

ACTIVE_STATUSES = ["pending", "confirmed", "checked_in"]


class ReservationError(Exception):
    pass


def create_reservation(user_id, event_id, table_id, guests_count):
    """Kreira rezervaciju; vraća (reservation_id, deposit_iznos)."""
    event = events_col.find_one({"_id": ObjectId(event_id)})
    if not event or event.get("is_cancelled"):
        raise ReservationError("Event ne postoji ili je otkazan")

    floor_map = floor_maps_col.find_one({
        "club_id": event["club_id"],
        "is_active": True,
        "tables.id": table_id,
    })
    if not floor_map:
        raise ReservationError("Stol ne postoji na mapi kluba")

    table = next((t for t in floor_map["tables"] if t["id"] == table_id), None)
    if not table:
        raise ReservationError("Stol ne postoji")

    if guests_count and table.get("capacity") and guests_count > table["capacity"]:
        raise ReservationError(f"Stol prima najviše {table['capacity']} gostiju")

    # Brza provjera radi ljepše poruke; stvarnu atomnost jamči unique indeks
    existing = table_reservations_col.find_one({
        "event_id": ObjectId(event_id),
        "table_id": table_id,
        "status": {"$in": ACTIVE_STATUSES},
    })
    if existing:
        raise ReservationError("Stol je već rezerviran")

    is_vip = table.get("type") == "vip_separe"
    deposit = float(table.get("deposit") or 0) if is_vip else 0.0
    cancellation_deadline = event["date"] - timedelta(hours=24)

    reservation = {
        "user_id": ObjectId(user_id),
        "event_id": ObjectId(event_id),
        "club_id": event["club_id"],
        "floor_map_id": floor_map["_id"],
        "table_id": table_id,
        "table_type": table.get("type", "standard"),
        "table_label": table.get("label", table_id),
        "section_id": table.get("section_id"),
        "guests_count": guests_count,
        "deposit_amount": deposit,
        "deposit_paid": False,
        "deposit_coupon_remaining": 0.0,
        "stripe_deposit_payment_intent": None,
        # VIP čeka uplatu depozita; ostali stolovi su odmah potvrđeni
        "status": "pending" if (is_vip and deposit > 0) else "confirmed",
        "active_hold": True,
        "cancellation_deadline": cancellation_deadline,
        "reminder_sent": False,
        "checked_in_at": None,
        "checked_in_by": None,
        "notes": None,
        "created_at": datetime.utcnow(),
    }

    try:
        result = table_reservations_col.insert_one(reservation)
    except DuplicateKeyError:
        raise ReservationError("Stol je već rezerviran")

    return str(result.inserted_id), deposit


def confirm_vip_deposit(reservation_id, amount_cents, stripe_pi_id):
    """Poziva se iz Stripe webhooka — depozit plaćen, rezervacija potvrđena."""
    amount_eur = amount_cents / 100
    table_reservations_col.update_one(
        {"_id": ObjectId(reservation_id)},
        {"$set": {
            "deposit_paid": True,
            "deposit_coupon_remaining": amount_eur,
            "stripe_deposit_payment_intent": stripe_pi_id,
            "status": "confirmed",
        }},
    )


def cancel_reservation(reservation_id, user_id=None):
    """Otkazuje rezervaciju; refund depozita samo ako je VIP + plaćen + na vrijeme."""
    query = {"_id": ObjectId(reservation_id)}
    if user_id is not None:
        query["user_id"] = ObjectId(user_id)

    reservation = table_reservations_col.find_one(query)
    if not reservation:
        raise ReservationError("Rezervacija ne postoji")
    if reservation["status"] in ("cancelled", "no_show"):
        raise ReservationError("Rezervacija je već otkazana")

    now = datetime.utcnow()
    on_time = now <= reservation["cancellation_deadline"]
    is_vip = reservation["table_type"] == "vip_separe"

    refunded = False
    if is_vip and reservation.get("deposit_paid") and on_time:
        if reservation.get("stripe_deposit_payment_intent"):
            stripe_service.refund_payment_intent(
                reservation["stripe_deposit_payment_intent"]
            )
            refunded = True

    table_reservations_col.update_one(
        {"_id": reservation["_id"]},
        {"$set": {"status": "cancelled", "active_hold": False, "cancelled_at": now}},
    )
    return reservation, refunded


def apply_coupon(reservation_id, order_total):
    """Primijeni VIP kupon na narudžbu, vrati (novi_total, primijenjen_iznos)."""
    r = table_reservations_col.find_one({"_id": ObjectId(reservation_id)})
    remaining = (r or {}).get("deposit_coupon_remaining", 0.0) or 0.0
    if remaining <= 0:
        return order_total, 0.0

    applied = round(min(remaining, order_total), 2)
    new_total = round(order_total - applied, 2)

    table_reservations_col.update_one(
        {"_id": ObjectId(reservation_id)},
        {"$inc": {"deposit_coupon_remaining": -applied}},
    )
    return new_total, applied


def checkin_reservation(reservation_id, staff_id):
    """Check-in gosta na ulazu (hostesa)."""
    reservation = table_reservations_col.find_one({"_id": ObjectId(reservation_id)})
    if not reservation:
        raise ReservationError("Rezervacija ne postoji")
    if reservation["status"] == "checked_in":
        raise ReservationError("Gost je već ušao")
    if reservation["status"] != "confirmed":
        raise ReservationError(f"Rezervacija nije potvrđena (status: {reservation['status']})")

    table_reservations_col.update_one(
        {"_id": reservation["_id"]},
        {"$set": {
            "status": "checked_in",
            "checked_in_at": datetime.utcnow(),
            "checked_in_by": ObjectId(staff_id),
        }},
    )
    return reservation
