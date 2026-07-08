"""
MongoDB konekcija i definicije kolekcija — NightClub Manager v2.

Sve kolekcije nove sheme na jednom mjestu + kreiranje indeksa pri startu.
"""

import os

from pymongo import ASCENDING, DESCENDING, MongoClient

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongo:27017")

client = MongoClient(MONGO_URI, connect=False)
db = client["mydb"]

superadmins_col = db["superadmins"]
clubs_col = db["clubs"]
club_admins_col = db["club_admins"]
hostesses_col = db["hostesses"]
waiters_col = db["waiters"]
users_col = db["users"]
events_col = db["events"]
tickets_col = db["tickets"]
floor_maps_col = db["floor_maps"]
table_reservations_col = db["table_reservations"]
menus_col = db["menus"]
drink_orders_col = db["drink_orders"]
reports_col = db["reports"]


def ensure_indexes():
    """
    Kreira sve indekse nove sheme. Idempotentno — pymongo preskače
    postojeće indekse s istim imenom i opcijama.
    """
    try:
        superadmins_col.create_index([("username", ASCENDING)], unique=True)

        clubs_col.create_index([("slug", ASCENDING)], unique=True)
        clubs_col.create_index([("location.city", ASCENDING)])
        clubs_col.create_index([("is_active", ASCENDING)])

        club_admins_col.create_index([("email", ASCENDING)], unique=True)
        club_admins_col.create_index([("club_id", ASCENDING)])

        hostesses_col.create_index([("email", ASCENDING)], unique=True)
        hostesses_col.create_index([("club_id", ASCENDING)])

        waiters_col.create_index([("email", ASCENDING)], unique=True)
        waiters_col.create_index([("club_id", ASCENDING)])

        users_col.create_index([("email", ASCENDING)], unique=True)
        users_col.create_index([("auth_provider_id", ASCENDING)], sparse=True)

        events_col.create_index([("club_id", ASCENDING)])
        events_col.create_index([("date", ASCENDING)])
        events_col.create_index([("is_published", ASCENDING)])

        tickets_col.create_index([("user_id", ASCENDING)])
        tickets_col.create_index([("event_id", ASCENDING)])
        tickets_col.create_index([("qr_code", ASCENDING)], unique=True)
        tickets_col.create_index([("stripe_payment_intent_id", ASCENDING)], sparse=True)
        # Za expiry task (pending karte starije od TTL-a)
        tickets_col.create_index([("status", ASCENDING), ("purchased_at", ASCENDING)])

        floor_maps_col.create_index([("club_id", ASCENDING)])

        table_reservations_col.create_index([("user_id", ASCENDING)])
        table_reservations_col.create_index([("event_id", ASCENDING)])
        # Za expiry task (pending rezervacije starije od TTL-a)
        table_reservations_col.create_index(
            [("status", ASCENDING), ("created_at", ASCENDING)]
        )
        # Garancija da jedan stol na jednom eventu drži najviše jedna aktivna
        # rezervacija (pending/confirmed/checked_in imaju active_hold=True).
        # Partial unique indeks jer Mongo ne podržava $in u partialFilterExpression.
        table_reservations_col.create_index(
            [("event_id", ASCENDING), ("table_id", ASCENDING)],
            unique=True,
            partialFilterExpression={"active_hold": True},
            name="uniq_active_table_per_event",
        )

        menus_col.create_index([("club_id", ASCENDING)])

        drink_orders_col.create_index([("event_id", ASCENDING)])
        drink_orders_col.create_index([("waiter_id", ASCENDING)])
        drink_orders_col.create_index([("table_reservation_id", ASCENDING)])
        drink_orders_col.create_index([("order_status", ASCENDING)])

        reports_col.create_index([("club_id", ASCENDING), ("date", DESCENDING)])

        print("[indexes] MongoDB indeksi (v2 shema) su osigurani.")
    except Exception as exc:
        print(f"[indexes] Greška pri kreiranju indeksa: {exc}")
