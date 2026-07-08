"""
Demo seed — realistični testni podaci kroz javni API.

Pokretanje (uz podignut stack i seedanog superadmina):
    docker compose exec backend python seed_demo.py

Kreira 4 kluba (Noa, Papaya, Revelin, Ritz) s eventima, tlocrtima,
menijima i osobljem, plus demo gosta. Idempotentno — klubovi koji već
postoje (po slugu) se preskaču.
"""

import os
import sys
from datetime import datetime, timedelta

import requests

BASE = os.environ.get("SEED_BASE_URL", "http://localhost:5000")
SA_USER = os.environ.get("SUPERADMIN_USERNAME", "superadmin")
SA_PASS = os.environ.get("SUPERADMIN_PASSWORD", "superadmin123")

GUEST_EMAIL = "gost@example.com"
GUEST_PASS = "lozinka123"


def _days(n, hour=23):
    return (datetime.utcnow() + timedelta(days=n)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    ).isoformat()


CLUBS = [
    {
        "club": {
            "name": "Noa Beach Club",
            "location": {"city": "Novalja", "address": "Zrće bb",
                         "coordinates": {"lat": 44.5405, "lng": 14.9095}},
            "description": "Beach klub na Zrću — pool partyji i internacionalni DJ-evi.",
            "capacity": 3500, "dress_code": "casual", "age_limit": 18,
            "amenities": ["bazen", "VIP separe", "parking", "pušačka zona"],
            "working_hours": "22:00 – 06:00",
            "social_links": {"instagram": "https://instagram.com/noabeachclub"},
        },
        "events": [
            {"name": "Noa Opening — Summer 2026", "genre": "EDM", "days": 7,
             "lineup": ["DJ Umek", "Insolate"],
             "ticket_types": [
                 {"name": "Early Bird", "price": 15.0, "total_quantity": 300},
                 {"name": "Regular", "price": 25.0, "total_quantity": 700},
                 {"name": "VIP", "price": 60.0, "total_quantity": 100},
             ]},
            {"name": "Techno Tuesday", "genre": "techno", "days": 12,
             "lineup": ["Ilario Alicante"],
             "ticket_types": [
                 {"name": "Regular", "price": 20.0, "total_quantity": 500},
             ]},
        ],
    },
    {
        "club": {
            "name": "Papaya",
            "location": {"city": "Novalja", "address": "Zrće bb",
                         "coordinates": {"lat": 44.5411, "lng": 14.9101}},
            "description": "Jedan od najpoznatijih open-air klubova Europe.",
            "capacity": 4000, "dress_code": "casual", "age_limit": 18,
            "amenities": ["bazen", "VIP separe", "fast food"],
            "working_hours": "23:00 – 06:00",
            "social_links": {"instagram": "https://instagram.com/papaya_zrce"},
        },
        "events": [
            {"name": "Papaya Day & Night", "genre": "house", "days": 9,
             "lineup": ["Solomun", "Adriatique"],
             "ticket_types": [
                 {"name": "Regular", "price": 30.0, "total_quantity": 1000},
                 {"name": "VIP", "price": 80.0, "total_quantity": 150},
             ]},
        ],
    },
    {
        "club": {
            "name": "Culture Club Revelin",
            "location": {"city": "Dubrovnik", "address": "Ul. Svetog Dominika 3",
                         "coordinates": {"lat": 42.6414, "lng": 18.1128}},
            "description": "Klub u tvrđavi staroj 500 godina, uz same zidine Dubrovnika.",
            "capacity": 1500, "dress_code": "smart casual", "age_limit": 21,
            "amenities": ["VIP separe", "terasa", "garderoba"],
            "working_hours": "23:00 – 06:00",
            "social_links": {"instagram": "https://instagram.com/culture_club_revelin"},
        },
        "events": [
            {"name": "Revelin Fortress Night", "genre": "EDM", "days": 5,
             "lineup": ["Timmy Trumpet"],
             "ticket_types": [
                 {"name": "Regular", "price": 35.0, "total_quantity": 400},
                 {"name": "VIP Fortress", "price": 100.0, "total_quantity": 50},
             ]},
            {"name": "RnB Fridays", "genre": "rnb", "days": 15,
             "lineup": ["DJ Phat Phillie"],
             "ticket_types": [
                 {"name": "Regular", "price": 18.0, "total_quantity": 350},
             ]},
        ],
    },
    {
        "club": {
            "name": "Ritz Club",
            "location": {"city": "Zagreb", "address": "Petrinjska 4",
                         "coordinates": {"lat": 45.8125, "lng": 15.9819}},
            "description": "Gradski klub u centru Zagreba — vikend program cijelu godinu.",
            "capacity": 800, "dress_code": "elegant", "age_limit": 21,
            "amenities": ["VIP separe", "garderoba", "šank na dvije etaže"],
            "working_hours": "23:00 – 05:00",
            "social_links": {"instagram": "https://instagram.com/ritzclubzagreb"},
        },
        "events": [
            {"name": "Ritz Saturday", "genre": "pop/rnb", "days": 3,
             "lineup": ["Rezidenti"],
             "ticket_types": [
                 {"name": "Regular", "price": 10.0, "total_quantity": 300},
                 {"name": "VIP", "price": 40.0, "total_quantity": 40},
             ]},
            # Neobjavljeni event — za test da se NE prikazuje javno
            {"name": "Private NYE Rehearsal", "genre": "pop", "days": 20,
             "is_published": False,
             "ticket_types": [
                 {"name": "Interno", "price": 0.0, "total_quantity": 50},
             ]},
        ],
    },
]


def floor_map_payload():
    tables = []
    # 6 standardnih stolova u dva reda (lijeva sekcija)
    for i in range(6):
        tables.append({
            "id": f"t-std-{i + 1}", "label": f"S{i + 1}", "type": "standard",
            "x": 8 + (i % 3) * 14, "y": 15 + (i // 3) * 22,
            "width": 8, "height": 8, "capacity": 4,
            "min_spend": 50, "deposit": 0, "section_id": "sec-left",
        })
    # 3 VIP separea (desna sekcija) — s depozitom
    for i in range(3):
        tables.append({
            "id": f"t-vip-{i + 1}", "label": f"VIP{i + 1}", "type": "vip_separe",
            "x": 65, "y": 12 + i * 25,
            "width": 12, "height": 12, "capacity": 8,
            "min_spend": 300, "deposit": 100, "section_id": "sec-right",
        })
    return {
        "name": "Glavni tlocrt",
        "width": 1000, "height": 700,
        "tables": tables,
        "sections": [
            {"id": "sec-left", "name": "Lijevo krilo", "color": "#CC00FF",
             "table_ids": [t["id"] for t in tables if t["section_id"] == "sec-left"]},
            {"id": "sec-right", "name": "VIP zona", "color": "#8B00CC",
             "table_ids": [t["id"] for t in tables if t["section_id"] == "sec-right"]},
        ],
    }


def menu_payload():
    return {
        "name": "Cjenik",
        "categories": [
            {"name": "Žestoka pića", "items": [
                {"id": "vodka", "name": "Vodka", "price": 6.0, "volume": "0.03l"},
                {"id": "gin-tonik", "name": "Gin tonik", "price": 8.0, "volume": "0.2l"},
                {"id": "jager", "name": "Jägermeister", "price": 5.0, "volume": "0.03l"},
                {"id": "tequila", "name": "Tequila", "price": 5.0, "volume": "0.03l"},
            ]},
            {"name": "Kokteli", "items": [
                {"id": "mojito", "name": "Mojito", "price": 10.0, "volume": "0.3l"},
                {"id": "aperol", "name": "Aperol Spritz", "price": 9.0, "volume": "0.3l"},
                {"id": "sotb", "name": "Sex on the Beach", "price": 10.0, "volume": "0.3l"},
            ]},
            {"name": "Boce", "items": [
                {"id": "moet", "name": "Moët & Chandon", "price": 150.0, "volume": "0.75l"},
                {"id": "grey-goose", "name": "Grey Goose", "price": 180.0, "volume": "0.7l"},
                {"id": "jack", "name": "Jack Daniel's", "price": 120.0, "volume": "0.7l"},
            ]},
            {"name": "Bezalkoholna", "items": [
                {"id": "voda", "name": "Voda", "price": 3.0, "volume": "0.5l"},
                {"id": "cola", "name": "Coca-Cola", "price": 4.0, "volume": "0.25l"},
                {"id": "redbull", "name": "Red Bull", "price": 6.0, "volume": "0.25l"},
            ]},
        ],
    }


def staff_payloads(slug):
    return [
        {"role": "hostess", "name": "Ana Anić", "email": f"ana@{slug}.hr", "pin": "1111"},
        {"role": "waiter", "name": "Ivan Ivić", "email": f"ivan@{slug}.hr", "pin": "2222",
         "assigned_sections": ["sec-left"]},
        {"role": "waiter", "name": "Marko Marić", "email": f"marko@{slug}.hr", "pin": "3333",
         "assigned_sections": ["sec-right"]},
    ]


def main():
    r = requests.post(f"{BASE}/api/auth/admin/login",
                      json={"email": SA_USER, "password": SA_PASS}, timeout=10)
    if r.status_code != 200:
        sys.exit(f"Superadmin login nije uspio ({r.status_code}) — pokreni seed_superadmin.py")
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    existing = {c["slug"] for c in requests.get(f"{BASE}/api/clubs", timeout=10).json()["clubs"]}

    for entry in CLUBS:
        name = entry["club"]["name"]
        r = requests.post(f"{BASE}/api/clubs", headers=headers, json=entry["club"], timeout=10)
        if r.status_code == 409:
            print(f"• {name} — već postoji, preskačem")
            continue
        if r.status_code != 201:
            sys.exit(f"Kreiranje kluba '{name}' nije uspjelo ({r.status_code}): {r.text[:200]}")
        club = r.json()
        club_id, slug = club["_id"], club["slug"]
        print(f"✔ Klub: {name} (slug: {slug})")

        r = requests.post(f"{BASE}/api/floor-maps?club_id={club_id}",
                          headers=headers, json=floor_map_payload(), timeout=10)
        print(f"  {'✔' if r.status_code == 201 else '✘'} tlocrt ({r.status_code})")

        r = requests.post(f"{BASE}/api/menu?club_id={club_id}",
                          headers=headers, json=menu_payload(), timeout=10)
        print(f"  {'✔' if r.status_code == 201 else '✘'} meni ({r.status_code})")

        for staff in staff_payloads(slug):
            r = requests.post(f"{BASE}/api/admin/staff?club_id={club_id}",
                              headers=headers, json=staff, timeout=10)
            ok = "✔" if r.status_code in (201, 409) else "✘"
            print(f"  {ok} osoblje: {staff['name']} [{staff['role']}] ({r.status_code})")

        for ev in entry["events"]:
            payload = {
                "club_id": club_id,
                "name": ev["name"],
                "date": _days(ev["days"]),
                "genre": ev.get("genre"),
                "lineup": ev.get("lineup", []),
                "is_published": ev.get("is_published", True),
                "ticket_types": ev["ticket_types"],
            }
            r = requests.post(f"{BASE}/api/events", headers=headers, json=payload, timeout=10)
            print(f"  {'✔' if r.status_code == 201 else '✘'} event: {ev['name']} ({r.status_code})")

    r = requests.post(f"{BASE}/api/auth/register", json={
        "email": GUEST_EMAIL, "password": GUEST_PASS, "name": "Demo Gost",
    }, timeout=10)
    if r.status_code == 201:
        print(f"✔ Demo gost: {GUEST_EMAIL} / {GUEST_PASS}")
    elif r.status_code == 409:
        print(f"• Demo gost {GUEST_EMAIL} već postoji")

    print("\nGotovo. Osoblje se prijavljuje s email + PIN (hostesa 1111, konobari 2222/3333).")


if __name__ == "__main__":
    main()
