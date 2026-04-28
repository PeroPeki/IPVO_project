from celery import Celery
from pymongo import MongoClient
from datetime import datetime
import time

import redis as redis_lib

from pipeline_task import (
    fetch_ticketmaster_events,
    get_lastfm_artist_data,
    encode_genre,
    calculate_base_price,
    compute_days_until_event,
    TARGET_CITIES,
)

# Inicijalizacija Celery aplikacije
app = Celery('tasks')
app.config_from_object('celery_config')


@app.task
def generate_daily_report():
    """Generira dnevni izvještaj agregata iz MongoDB-a."""
    print("Generiranje dnevnog izvještaja...")

    client = MongoClient("mongodb://mongo:27017")
    db = client["mydb"]

    total_reservations = db.reservations.count_documents({})
    total_tickets = db.tickets.count_documents({})

    report = {
        "date": datetime.utcnow().isoformat(),
        "type": "DAILY_STATS",
        "metrics": {
            "total_reservations": total_reservations,
            "total_tickets_sold": total_tickets,
            "revenue_estimate": total_tickets * 10,
        },
    }

    db.reports.insert_one(report)
    print(f"Izvještaj spremljen! ID: {report['_id']}")
    client.close()


@app.task
def run_data_pipeline():
    """
    Glavni Celery task koji okida data pipeline:
    Ticketmaster → Last.fm → MongoDB upsert + invalidacija Redis cachea.
    """
    client = MongoClient("mongodb://mongo:27017")
    db = client["mydb"]
    cache = redis_lib.Redis(host="redis", port=6379, db=0)
    total_upserted = 0

    for city, country_code in TARGET_CITIES:
        print(f"Obrada grada: {city}")
        events = fetch_ticketmaster_events(city, country_code)

        for event in events:
            time.sleep(0.3)  # Last.fm rate-limit pauza
            lastfm_data = get_lastfm_artist_data(event["artist_name"])
            genre_encoded = encode_genre(lastfm_data["artist_tags"])
            days_until = compute_days_until_event(event.get("event_date"))
            base_price = calculate_base_price(
                lastfm_data["artist_listeners"],
                event.get("venue_capacity"),
                days_until,
                genre_encoded,
            )

            event_doc = {
                **event,
                **lastfm_data,
                "genre_encoded": genre_encoded,
                "days_until_event": days_until,
                "base_price": base_price,
                "current_price": base_price,
                "min_price": round(base_price * 0.5, 2),
                "max_price": round(base_price * 2.5, 2),
                "source": "ticketmaster",
                "pipeline_updated_at": datetime.utcnow(),
            }

            result = db.events.update_one(
                {"ticketmaster_id": event["ticketmaster_id"]},
                {"$set": event_doc},
                upsert=True,
            )
            if result.upserted_id:
                total_upserted += 1

            cache.delete(f"events_city_{city.lower()}")
        time.sleep(1)

    print(f"Pipeline završen: {total_upserted} novih evenata")
    client.close()
