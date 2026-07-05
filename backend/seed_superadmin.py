"""
Kreira inicijalnog superadmina (idempotentno).

Pokretanje:
    docker compose exec backend python seed_superadmin.py
Pristupni podaci se čitaju iz SUPERADMIN_USERNAME / SUPERADMIN_PASSWORD
env varijabli (default: superadmin / superadmin123 — promijeni u produkciji!).
"""

import os
from datetime import datetime

from pymongo import MongoClient
from werkzeug.security import generate_password_hash

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongo:27017")
USERNAME = os.environ.get("SUPERADMIN_USERNAME", "superadmin")
PASSWORD = os.environ.get("SUPERADMIN_PASSWORD", "superadmin123")


def seed():
    client = MongoClient(MONGO_URI)
    db = client["mydb"]

    if db.superadmins.find_one({"username": USERNAME}):
        print(f"Superadmin '{USERNAME}' već postoji — ništa za napraviti.")
        return

    db.superadmins.insert_one({
        "username": USERNAME,
        "password_hash": generate_password_hash(PASSWORD),
        "role": "superadmin",
        "created_at": datetime.utcnow(),
    })
    print(f"Superadmin '{USERNAME}' kreiran.")
    client.close()


if __name__ == "__main__":
    seed()
