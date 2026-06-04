import os
from celery import Celery
from pymongo import MongoClient
from datetime import datetime
import time

import pylast
import redis as redis_lib

from pipeline_task import (
    fetch_ticketmaster_events,
    get_lastfm_artist_data,
    encode_genre,
    calculate_base_price,
    compute_days_until_event,
    compute_day_of_week,
    compute_default_tickets_sold_ratio,
    slugify,
    TARGET_CITIES,
    DEFAULT_VENUE_CAPACITY,
    GENRE_MAP,
)

LASTFM_KEY = os.environ.get("LASTFM_API_KEY")

# Inicijalizacija Celery aplikacije
app = Celery('tasks')
app.config_from_object('celery_config')


def _ensure_indexes_worker():
    """Osigurava MongoDB indekse pri startu analytics_workera (idempotentno)."""
    try:
        _client = MongoClient("mongodb://mongo:27017")
        _db = _client["mydb"]
        _db["events"].create_index([("ticketmaster_id", 1)], unique=True, sparse=True)
        _db["events"].create_index([("club_id", 1)])
        _db["tables"].create_index([("event_id", 1)])
        _db["price_log"].create_index([("timestamp", -1)])
        _db["ml_training_data"].create_index([("artist_name", 1)])
        _client.close()
        print("[worker-indexes] MongoDB indeksi osigurani.")
    except Exception as exc:
        print(f"[worker-indexes] Greška: {exc}")


_ensure_indexes_worker()


GENRE_NAME_BY_CODE = {v: k for k, v in GENRE_MAP.items()}


def _ensure_club(db, event):
    """Upsertaj klub (venue) iz Ticketmaster eventa i vrati njegov stabilan id."""
    venue_id = event.get("venue_id")
    venue_name = event.get("venue_name") or "Unknown Venue"
    venue_city = event.get("city") or "Unknown"
    venue_country = event.get("country") or "??"

    club_id = f"tm-{venue_id}" if venue_id else f"venue-{slugify(venue_name)}-{slugify(venue_city)}"

    location_parts = [p for p in [venue_city, event.get("country_name") or venue_country] if p]
    location = ", ".join(location_parts)

    description_bits = []
    if event.get("venue_address"):
        description_bits.append(event["venue_address"])
    if event.get("venue_capacity"):
        description_bits.append(f"Kapacitet: {event['venue_capacity']}")
    if not description_bits:
        description_bits.append(f"Klupski/koncertni venue u gradu {venue_city}.")

    club_doc = {
        "id": club_id,
        "name": venue_name,
        "city": venue_city,
        "country": venue_country,
        "country_name": event.get("country_name"),
        "location": location,
        "address": event.get("venue_address"),
        "postal_code": event.get("venue_postal_code"),
        "venue_capacity": event.get("venue_capacity"),
        "latitude": event.get("venue_latitude"),
        "longitude": event.get("venue_longitude"),
        "external_url": event.get("venue_url"),
        "description": " · ".join(description_bits),
        "source": "ticketmaster",
        "updated_at": datetime.utcnow(),
    }

    db.clubs.update_one({"id": club_id}, {"$set": club_doc}, upsert=True)
    return club_id


def _ensure_tables(db, event_id, base_price, table_count=20):
    """Kreiraj stolove za event ako još ne postoje. Deterministički raspored cijena."""
    if db.tables.count_documents({"event_id": event_id}) > 0:
        return 0

    tables = []
    for i in range(1, table_count + 1):
        capacity = ((i - 1) % 4) + 2  # 2..5 osoba
        table_price = round(base_price * capacity * 0.3, 2)
        tables.append({
            "id": f"{event_id}-table-{i}",
            "event_id": event_id,
            "number": i,
            "capacity": capacity,
            "status": "free",
            "price": table_price,
        })
    if tables:
        db.tables.insert_many(tables)
    return len(tables)


@app.task
def generate_daily_report():
    """Generira dnevni izvještaj agregata iz MongoDB-a."""
    print("Generiranje dnevnog izvještaja...")

    client = MongoClient("mongodb://mongo:27017")
    db = client["mydb"]

    total_reservations = db.reservations.count_documents({})
    total_tickets = db.tickets.count_documents({})

    revenue_pipeline = [
        {"$group": {"_id": None, "total_revenue": {"$sum": "$price"}}}
    ]
    revenue_result = list(db.tickets.aggregate(revenue_pipeline))
    revenue_estimate = revenue_result[0]["total_revenue"] if revenue_result else 0

    report = {
        "date": datetime.utcnow().isoformat(),
        "type": "DAILY_STATS",
        "metrics": {
            "total_reservations": total_reservations,
            "total_tickets_sold": total_tickets,
            "revenue_estimate": round(revenue_estimate or 0, 2),
        },
    }

    db.reports.insert_one(report)
    print(f"Izvještaj spremljen! ID: {report['_id']}")
    client.close()


@app.task
def run_data_pipeline():
    """
    Glavni Celery task: Ticketmaster → Last.fm → Mongo upsert klubova/eventa/stolova.

    Svaki Ticketmaster venue postaje "klub" u našem sustavu.
    Eventi se povezuju s klubom preko `club_id`.
    Za svaki event automatski se generiraju stolovi (ako ne postoje).
    """
    client = MongoClient("mongodb://mongo:27017")
    db = client["mydb"]
    cache = redis_lib.Redis(host="redis", port=6379, db=0)

    # Inicijaliziraj Last.fm network jednom za cijeli pipeline (umjesto per-artist)
    lastfm_network = None
    if LASTFM_KEY:
        try:
            lastfm_network = pylast.LastFMNetwork(api_key=LASTFM_KEY)
        except Exception as exc:
            print(f"Last.fm inicijalizacija greška: {exc}")

    stats = {
        "cities_processed": 0,
        "cities_skipped": 0,
        "events_upserted": 0,
        "events_new": 0,
        "clubs_upserted": 0,
        "tables_created": 0,
    }
    seen_club_ids = set()

    for city, country_code in TARGET_CITIES:
        print(f"Obrada grada: {city}, {country_code}")
        try:
            events = fetch_ticketmaster_events(city, country_code)
        except Exception as exc:
            print(f"  Pad pri dohvatu {city}: {exc}")
            stats["cities_skipped"] += 1
            continue

        if not events:
            print(f"  Nema rezultata za {city}, preskačem.")
            stats["cities_skipped"] += 1
            continue

        stats["cities_processed"] += 1

        for event in events:
            time.sleep(0.3)  # Last.fm rate-limit pauza

            # 1. Klub iz venuea
            club_id = _ensure_club(db, event)
            if club_id not in seen_club_ids:
                seen_club_ids.add(club_id)
                stats["clubs_upserted"] += 1

            # 2. Last.fm obogaćivanje (reuse jedne network instance)
            lastfm_data = get_lastfm_artist_data(event["artist_name"], network=lastfm_network)
            genre_encoded = encode_genre(lastfm_data["artist_tags"])
            genre_name = GENRE_NAME_BY_CODE.get(genre_encoded, "other")

            # 3. Vremenski podaci
            days_until = compute_days_until_event(event.get("event_date"))
            day_of_week = compute_day_of_week(event.get("event_date"))
            venue_capacity = event.get("venue_capacity") or DEFAULT_VENUE_CAPACITY
            tickets_sold_ratio = compute_default_tickets_sold_ratio(days_until)

            # 4. Cijena (ML feature alignment)
            base_price = calculate_base_price(
                lastfm_data["artist_listeners"],
                venue_capacity,
                days_until,
                genre_encoded,
            )

            event_id = event["ticketmaster_id"]

            # Frontend čita events.id; ostavljamo isti kao TM id radi jednostavnosti.
            event_doc = {
                **event,
                **lastfm_data,
                "id": event_id,
                "club_id": club_id,
                "venue_capacity": venue_capacity,
                "genre_encoded": genre_encoded,
                "genre_name": genre_name,
                "days_until_event": days_until,
                "day_of_week": day_of_week,
                "tickets_sold_ratio": tickets_sold_ratio,
                "base_price": base_price,
                "min_price": round(base_price * 0.5, 2),
                "max_price": round(base_price * 2.5, 2),
                "description": _build_event_description(event, lastfm_data, genre_name),
                "date": event.get("event_date_local"),
                "source": "ticketmaster",
                "pipeline_updated_at": datetime.utcnow(),
            }

            # Datum iz Pythonovog datetime objekta u Mongo
            if event_doc.get("event_date"):
                event_doc["event_date"] = event_doc["event_date"].isoformat()

            result = db.events.update_one(
                {"ticketmaster_id": event_id},
                {
                    "$set": event_doc,
                    "$setOnInsert": {"current_price": base_price},
                },
                upsert=True,
            )
            stats["events_upserted"] += 1
            if result.upserted_id:
                stats["events_new"] += 1

            # 5. Stolovi za event (samo ako još ne postoje)
            tables_added = _ensure_tables(db, event_id, base_price)
            stats["tables_created"] += tables_added

            # 6. Cache invalidacija
            cache.delete(f"events_city_{city.lower()}")
            cache.delete(f"event_pricing_{event_id}")
            cache.delete(f"tables_list_{event_id}")

        cache.delete("clubs_list")
        cache.delete("events_global")
        time.sleep(1)

    print(f"Pipeline gotov: {stats}")
    client.close()
    return stats


@app.task
def run_generate_training_data():
    """Celery task koji pokreće generator training podataka."""
    try:
        import subprocess
        result = subprocess.run(
            ["python", "generate_training_data.py"],
            capture_output=True, text=True, timeout=1800,
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"Generator greška: {result.stderr}")
    except Exception as exc:
        print(f"Greška pri generiranju training podataka: {exc}")


@app.task
def run_train_model():
    """Celery task koji pokreće trening modela."""
    try:
        import subprocess
        result = subprocess.run(
            ["python", "train_model.py"],
            capture_output=True, text=True, timeout=3600,
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"Trening greška: {result.stderr}")
    except Exception as exc:
        print(f"Greška pri treniranju modela: {exc}")


def _build_event_description(event, lastfm_data, genre_name):
    parts = []
    if event.get("tm_genre"):
        parts.append(f"Žanr: {event['tm_genre']}")
    elif genre_name and genre_name != "other":
        parts.append(f"Žanr: {genre_name}")
    if event.get("venue_name"):
        parts.append(f"Venue: {event['venue_name']}")
    if event.get("city"):
        parts.append(f"Lokacija: {event['city']}")
    if lastfm_data.get("artist_listeners"):
        parts.append(f"Last.fm slušatelji: {lastfm_data['artist_listeners']:,}")
    if event.get("info"):
        parts.append(event["info"][:200])
    return " · ".join(parts) or "Glazbeni event"
