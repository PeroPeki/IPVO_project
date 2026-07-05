"""
Migracija v1 → v2: briše kolekcije starog (ML/Ticketmaster) formata.

Nova shema je potpuno drugačija pa se stari podaci ne prenose.
Pokretanje:
    docker compose exec backend python migrate_v2.py
"""

import os

from pymongo import MongoClient

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongo:27017")

# Kolekcije v1 sustava koje se uklanjaju
OLD_COLLECTIONS = [
    # ML / dinamičke cijene
    "ml_training_data",
    "price_log",
    "model_metadata",
    # Stari format podataka (Ticketmaster pipeline)
    "events",
    "clubs",
    "tables",            # zamijenjeno s floor_maps
    "reservations",      # zamijenjeno s table_reservations
    # Stari user/ticket format (samo username, bez auth) — nekompatibilno
    "users",
    "tickets",
    "reports",
]


def run_migration():
    client = MongoClient(MONGO_URI)
    db = client["mydb"]
    existing = set(db.list_collection_names())

    print("=== Migracija NightClub Manager v1 → v2 ===")
    for name in OLD_COLLECTIONS:
        if name in existing:
            count = db[name].estimated_document_count()
            db[name].drop()
            print(f"  ✔ Obrisana kolekcija '{name}' ({count} dokumenata)")
        else:
            print(f"  - Kolekcija '{name}' ne postoji, preskačem")

    # Novi indeksi
    import db as db_module
    db_module.ensure_indexes()

    print("Migracija gotova. Nova shema kreira se kroz ensure_indexes() pri startu.")
    client.close()


if __name__ == "__main__":
    run_migration()
