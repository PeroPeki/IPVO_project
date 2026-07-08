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

# Neplaćena VIP rezervacija drži stol najviše ovoliko minuta (Celery je oslobađa)
PENDING_DEPOSIT_TTL_MINUTES = 15


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
    """
    Poziva se iz Stripe webhooka — depozit plaćen, rezervacija potvrđena.

    Vraća True ako je rezervacija potvrđena. Ako je u međuvremenu istekla
    (deposit_timeout), pokušava je oživjeti; ako je stol već preuzet,
    depozit se automatski refundira i vraća se False.
    """
    oid = ObjectId(reservation_id)
    amount_eur = amount_cents / 100
    updates = {
        "deposit_paid": True,
        "deposit_coupon_remaining": amount_eur,
        "stripe_deposit_payment_intent": stripe_pi_id,
        "status": "confirmed",
    }

    existing = table_reservations_col.find_one({"_id": oid})
    if not existing:
        return False
    if existing.get("deposit_paid"):
        return True  # webhook retry — već obrađeno

    result = table_reservations_col.update_one(
        {"_id": oid, "status": "pending"}, {"$set": updates}
    )
    if result.modified_count:
        return True

    # Rezervacija je istekla prije uplate — oživi je ako je stol još slobodan
    # (unique indeks na (event_id, table_id) štiti od dvostrukog zauzeća)
    try:
        revived = table_reservations_col.update_one(
            {"_id": oid, "status": "cancelled", "cancel_reason": "deposit_timeout"},
            {"$set": {**updates, "active_hold": True}},
        )
        if revived.modified_count:
            return True
    except DuplicateKeyError:
        pass

    # Stol više nije dostupan → vrati depozit
    try:
        stripe_service.refund_payment_intent(stripe_pi_id)
        table_reservations_col.update_one(
            {"_id": oid},
            {"$set": {"refund_status": "refunded",
                      "stripe_deposit_payment_intent": stripe_pi_id}},
        )
    except Exception as exc:
        table_reservations_col.update_one(
            {"_id": oid},
            {"$set": {"refund_status": "failed", "refund_error": str(exc),
                      "stripe_deposit_payment_intent": stripe_pi_id}},
        )
    return False


def cancel_reservation(reservation_id, user_id=None):
    """Otkazuje rezervaciju; refund depozita samo ako je VIP + plaćen + na vrijeme."""
    query = {"_id": ObjectId(reservation_id)}
    if user_id is not None:
        query["user_id"] = ObjectId(user_id)

    if not table_reservations_col.find_one(query):
        raise ReservationError("Rezervacija ne postoji")

    now = datetime.utcnow()
    # Atomarno preuzmi otkazivanje — paralelni zahtjevi ne mogu dvaput refundirati
    reservation = table_reservations_col.find_one_and_update(
        {**query, "status": {"$in": ACTIVE_STATUSES}},
        {"$set": {"status": "cancelled", "active_hold": False, "cancelled_at": now}},
    )
    if not reservation:
        raise ReservationError("Rezervacija je već otkazana")

    on_time = now <= reservation["cancellation_deadline"]
    is_vip = reservation["table_type"] == "vip_separe"

    refunded = False
    if (is_vip and reservation.get("deposit_paid") and on_time
            and reservation.get("stripe_deposit_payment_intent")):
        try:
            stripe_service.refund_payment_intent(
                reservation["stripe_deposit_payment_intent"]
            )
            refunded = True
            table_reservations_col.update_one(
                {"_id": reservation["_id"]},
                {"$set": {"refund_status": "refunded",
                          "deposit_coupon_remaining": 0.0}},
            )
        except Exception as exc:
            # Rezervacija ostaje otkazana; refund se rješava ručno iz admina
            table_reservations_col.update_one(
                {"_id": reservation["_id"]},
                {"$set": {"refund_status": "failed", "refund_error": str(exc)}},
            )
    return reservation, refunded


def apply_coupon(reservation_id, order_total):
    """
    Primijeni VIP kupon na narudžbu, vrati (novi_total, primijenjen_iznos).

    Guard uvjet ($gte) u update upitu sprječava da dvije istovremene narudžbe
    potroše isti iznos kupona; pri neuspjehu se stanje ponovno pročita.
    """
    oid = ObjectId(reservation_id)
    for _ in range(3):
        r = table_reservations_col.find_one(
            {"_id": oid}, {"deposit_coupon_remaining": 1}
        )
        remaining = (r or {}).get("deposit_coupon_remaining") or 0.0
        applied = round(min(remaining, order_total), 2)
        if applied <= 0:
            return order_total, 0.0

        result = table_reservations_col.update_one(
            {"_id": oid, "deposit_coupon_remaining": {"$gte": applied}},
            {"$inc": {"deposit_coupon_remaining": -applied}},
        )
        if result.modified_count:
            return round(order_total - applied, 2), applied
    return order_total, 0.0


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
