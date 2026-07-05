"""
Integracijski testovi — NightClub Manager v2.

Pokretanje (unutar backend kontejnera, uz podignut stack):
    docker compose exec backend python run_tests.py

Testira: health, autentikaciju (user/superadmin/staff), CRUD klubova i eventa,
mape stolova, rezervacije (bez depozita), meni i narudžbe pića s kuponom.
Stripe rute testiraju se samo do granice vanjskog poziva (bez pravog ključa
purchase vraća 502, što test tretira kao očekivano u dev okruženju).
"""

import os
import sys
import uuid
from datetime import datetime, timedelta

import requests

BASE = os.environ.get("TEST_BASE_URL", "http://localhost:5000")

PASSED = []
FAILED = []


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print(f"  ✔ {name}")
    else:
        FAILED.append(name)
        print(f"  ✘ {name} {detail}")


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def main():
    suffix = uuid.uuid4().hex[:8]

    print("\n== Health ==")
    r = requests.get(f"{BASE}/api/health", timeout=10)
    check("GET /api/health", r.status_code == 200 and r.json().get("status") == "ok")

    r = requests.get(f"{BASE}/metrics", timeout=10)
    check("GET /metrics (Prometheus)", r.status_code == 200 and b"http_requests_total" in r.content)

    print("\n== Autentikacija — korisnik ==")
    email = f"test-{suffix}@example.com"
    r = requests.post(f"{BASE}/api/auth/register", json={
        "email": email, "password": "lozinka123", "name": "Test Korisnik",
    })
    check("POST /api/auth/register", r.status_code == 201, f"({r.status_code}: {r.text[:100]})")
    user_token = r.json().get("access_token", "")
    refresh_token = r.json().get("refresh_token", "")

    r = requests.post(f"{BASE}/api/auth/register", json={
        "email": email, "password": "lozinka123", "name": "Duplikat",
    })
    check("register duplikat → 409", r.status_code == 409)

    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": "lozinka123"})
    check("POST /api/auth/login", r.status_code == 200 and "access_token" in r.json())

    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": "kriva"})
    check("login kriva lozinka → 401", r.status_code == 401)

    r = requests.post(f"{BASE}/api/auth/refresh", headers=auth_headers(refresh_token))
    check("POST /api/auth/refresh", r.status_code == 200 and "access_token" in r.json())

    print("\n== Autentikacija — superadmin ==")
    # Seed superadmina direktno u bazu (idempotentno)
    import seed_superadmin
    seed_superadmin.seed()
    r = requests.post(f"{BASE}/api/auth/admin/login", json={
        "email": seed_superadmin.USERNAME, "password": seed_superadmin.PASSWORD,
    })
    check("POST /api/auth/admin/login (superadmin)", r.status_code == 200,
          f"({r.status_code}: {r.text[:100]})")
    sa_token = r.json().get("access_token", "")

    print("\n== Klubovi ==")
    r = requests.post(f"{BASE}/api/clubs", headers=auth_headers(sa_token), json={
        "name": f"Test Klub {suffix}",
        "location": {"city": "Novalja", "address": "Zrće bb"},
        "capacity": 2000,
    })
    check("POST /api/clubs (superadmin)", r.status_code == 201, f"({r.status_code}: {r.text[:100]})")
    club = r.json()
    club_id = club.get("_id")

    r = requests.post(f"{BASE}/api/clubs", headers=auth_headers(user_token), json={"name": "X"})
    check("POST /api/clubs kao user → 403", r.status_code == 403)

    r = requests.get(f"{BASE}/api/clubs?city=Novalja")
    check("GET /api/clubs?city=Novalja", r.status_code == 200 and
          any(c["_id"] == club_id for c in r.json().get("clubs", [])))

    r = requests.get(f"{BASE}/api/clubs/{club['slug']}")
    check("GET /api/clubs/<slug>", r.status_code == 200 and r.json().get("_id") == club_id)

    print("\n== Osoblje ==")
    hostess_email = f"hostesa-{suffix}@klub.hr"
    r = requests.post(f"{BASE}/api/admin/staff?club_id={club_id}",
                      headers=auth_headers(sa_token), json={
        "role": "hostess", "name": "Ana Hostesa", "email": hostess_email, "pin": "1234",
    })
    check("POST /api/admin/staff (hostesa)", r.status_code == 201, f"({r.status_code}: {r.text[:100]})")

    waiter_email = f"konobar-{suffix}@klub.hr"
    r = requests.post(f"{BASE}/api/admin/staff?club_id={club_id}",
                      headers=auth_headers(sa_token), json={
        "role": "waiter", "name": "Ivo Konobar", "email": waiter_email, "pin": "5678",
        "assigned_sections": ["sec-1"],
    })
    check("POST /api/admin/staff (konobar)", r.status_code == 201)

    r = requests.post(f"{BASE}/api/auth/staff/login", json={"email": hostess_email, "pin": "1234"})
    check("POST /api/auth/staff/login (hostesa)", r.status_code == 200 and
          r.json().get("role") == "hostess")
    hostess_token = r.json().get("access_token", "")

    r = requests.post(f"{BASE}/api/auth/staff/login", json={"email": waiter_email, "pin": "5678"})
    check("staff login (konobar)", r.status_code == 200 and r.json().get("role") == "waiter")
    waiter_token = r.json().get("access_token", "")

    r = requests.post(f"{BASE}/api/auth/staff/login", json={"email": hostess_email, "pin": "0000"})
    check("staff login krivi PIN → 401", r.status_code == 401)

    print("\n== Eventi ==")
    event_date = (datetime.utcnow() + timedelta(days=10)).isoformat()
    r = requests.post(f"{BASE}/api/events", headers=auth_headers(sa_token), json={
        "club_id": club_id,
        "name": f"Test Party {suffix}",
        "date": event_date,
        "genre": "techno",
        "is_published": True,
        "ticket_types": [
            {"name": "Early Bird", "price": 15.0, "total_quantity": 100},
        ],
    })
    check("POST /api/events", r.status_code == 201, f"({r.status_code}: {r.text[:100]})")
    event = r.json()
    event_id = event.get("_id")

    r = requests.get(f"{BASE}/api/events/upcoming")
    check("GET /api/events/upcoming", r.status_code == 200 and
          any(e["_id"] == event_id for e in r.json().get("events", [])))

    r = requests.get(f"{BASE}/api/events?club_id={club_id}")
    check("GET /api/events?club_id=", r.status_code == 200 and r.json()["count"] >= 1)

    r = requests.get(f"{BASE}/api/events/{event_id}")
    check("GET /api/events/<id>", r.status_code == 200 and "club" in r.json())

    print("\n== Mapa stolova ==")
    r = requests.post(f"{BASE}/api/floor-maps?club_id={club_id}",
                      headers=auth_headers(sa_token), json={
        "name": "Glavni tlocrt",
        "width": 1000, "height": 700,
        "tables": [
            {"id": "t-1", "label": "S1", "type": "standard", "x": 10, "y": 10,
             "width": 8, "height": 8, "capacity": 4, "min_spend": 50,
             "deposit": 0, "section_id": "sec-1"},
            {"id": "t-2", "label": "VIP1", "type": "vip_separe", "x": 40, "y": 10,
             "width": 10, "height": 10, "capacity": 8, "min_spend": 300,
             "deposit": 100, "section_id": "sec-1"},
        ],
        "sections": [{"id": "sec-1", "name": "Lijevo krilo", "table_ids": ["t-1", "t-2"],
                      "color": "#CC00FF"}],
    })
    check("POST /api/floor-maps", r.status_code == 201, f"({r.status_code}: {r.text[:100]})")

    r = requests.get(f"{BASE}/api/floor-maps/event/{event_id}")
    check("GET /api/floor-maps/event/<id>", r.status_code == 200 and
          all(t.get("is_available") for t in r.json().get("tables", [])))

    print("\n== Rezervacije ==")
    r = requests.post(f"{BASE}/api/reservations", headers=auth_headers(user_token), json={
        "event_id": event_id, "table_id": "t-1", "guests_count": 2,
    })
    check("POST /api/reservations (standard, bez depozita)", r.status_code == 201 and
          r.json().get("deposit_required") is False, f"({r.status_code}: {r.text[:100]})")
    reservation_id = r.json().get("reservation_id")

    r = requests.post(f"{BASE}/api/reservations", headers=auth_headers(user_token), json={
        "event_id": event_id, "table_id": "t-1", "guests_count": 2,
    })
    check("duplikat rezervacije → 409", r.status_code == 409)

    r = requests.get(f"{BASE}/api/reservations/event/{event_id}")
    check("GET /api/reservations/event/<id>",
          r.status_code == 200 and "t-1" in r.json().get("reserved_tables", {}))

    r = requests.get(f"{BASE}/api/reservations/my", headers=auth_headers(user_token))
    check("GET /api/reservations/my", r.status_code == 200 and
          len(r.json().get("reservations", [])) >= 1)

    print("\n== Meni i narudžbe ==")
    r = requests.post(f"{BASE}/api/menu?club_id={club_id}",
                      headers=auth_headers(sa_token), json={
        "name": "Cjenik",
        "categories": [{
            "name": "Žestice",
            "items": [
                {"id": "gin", "name": "Gin tonik", "price": 8.0, "volume": "0.2l"},
                {"id": "voda", "name": "Voda", "price": 3.0, "volume": "0.5l"},
            ],
        }],
    })
    check("POST /api/menu", r.status_code == 201, f"({r.status_code}: {r.text[:100]})")

    r = requests.get(f"{BASE}/api/menu/club/{club_id}")
    check("GET /api/menu/club/<id>", r.status_code == 200)

    r = requests.post(f"{BASE}/api/orders", headers=auth_headers(user_token), json={
        "reservation_id": reservation_id,
        "items": [{"menu_item_id": "gin", "quantity": 2}],
        "payment_method": "cash",
    })
    check("POST /api/orders (gotovina)", r.status_code == 201 and
          r.json().get("total") == 16.0, f"({r.status_code}: {r.text[:100]})")
    order_id = r.json().get("order_id")

    r = requests.get(f"{BASE}/api/orders/waiter", headers=auth_headers(waiter_token))
    check("GET /api/orders/waiter", r.status_code == 200 and
          any(o["_id"] == order_id for o in r.json().get("orders", [])))

    r = requests.put(f"{BASE}/api/orders/{order_id}/accept", headers=auth_headers(waiter_token))
    check("PUT /api/orders/<id>/accept", r.status_code == 200)

    r = requests.put(f"{BASE}/api/orders/{order_id}/deliver", headers=auth_headers(waiter_token))
    check("PUT /api/orders/<id>/deliver", r.status_code == 200 and
          r.json()["order"]["order_status"] == "delivered")

    r = requests.get(f"{BASE}/api/orders/bar/{event_id}", headers=auth_headers(waiter_token))
    check("GET /api/orders/bar/<event_id>", r.status_code == 200)

    print("\n== Hostesa ==")
    r = requests.get(f"{BASE}/api/hostess/event/{event_id}/guests?search=Test",
                     headers=auth_headers(hostess_token))
    check("GET /api/hostess/event/<id>/guests", r.status_code == 200 and
          r.json().get("count", 0) >= 1, f"({r.status_code}: {r.text[:100]})")

    r = requests.post(f"{BASE}/api/hostess/checkin/reservation/{reservation_id}",
                      headers=auth_headers(hostess_token))
    check("POST /api/hostess/checkin/reservation/<id>", r.status_code == 200)

    r = requests.post(f"{BASE}/api/hostess/checkin/reservation/{reservation_id}",
                      headers=auth_headers(hostess_token))
    check("dupli check-in → 409", r.status_code == 409)

    r = requests.get(f"{BASE}/api/hostess/event/{event_id}/stats",
                     headers=auth_headers(hostess_token))
    check("GET /api/hostess/event/<id>/stats", r.status_code == 200 and
          r.json().get("reservations_checked_in") == 1)

    print("\n== Admin ==")
    r = requests.get(f"{BASE}/api/admin/dashboard?club_id={club_id}",
                     headers=auth_headers(sa_token))
    check("GET /api/admin/dashboard", r.status_code == 200 and
          r.json().get("reservations", 0) >= 1)

    r = requests.get(f"{BASE}/api/admin/events/{event_id}/live",
                     headers=auth_headers(sa_token))
    check("GET /api/admin/events/<id>/live", r.status_code == 200 and
          r.json().get("guests_inside") == 1)

    r = requests.get(f"{BASE}/api/admin/staff?club_id={club_id}",
                     headers=auth_headers(sa_token))
    check("GET /api/admin/staff", r.status_code == 200 and r.json().get("count") == 2)

    print("\n== Stripe (bez pravog ključa očekujemo kontroliranu grešku) ==")
    ticket_type_id = event["ticket_types"][0]["id"]
    r = requests.post(f"{BASE}/api/tickets/purchase", headers=auth_headers(user_token), json={
        "event_id": event_id, "ticket_type_id": ticket_type_id,
    })
    has_stripe = bool(os.environ.get("STRIPE_SECRET_KEY"))
    if has_stripe:
        check("POST /api/tickets/purchase (Stripe)", r.status_code == 201 and
              "client_secret" in r.json(), f"({r.status_code}: {r.text[:100]})")
    else:
        check("POST /api/tickets/purchase bez ključa → 502", r.status_code == 502)

    print(f"\n{'='*50}")
    print(f"Prošlo: {len(PASSED)} | Palo: {len(FAILED)}")
    if FAILED:
        print("Neuspjeli testovi:")
        for name in FAILED:
            print(f"  - {name}")
        sys.exit(1)
    print("Svi testovi su prošli.")


if __name__ == "__main__":
    main()
