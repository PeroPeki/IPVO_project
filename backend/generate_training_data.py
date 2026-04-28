"""
Pricing Training Data Generator
- Dohvaća STVARNE izvođače s Last.fm (tag.gettopartists)
- Generira training zapise kombinacijom scenarija kapaciteta i dana
- Cijene izračunava determinističkom formulom (bez Fakera, bez randoma)
"""

import os
import math
import time
from datetime import datetime

import requests
import pylast
from pymongo import MongoClient


LASTFM_KEY = os.environ.get("LASTFM_API_KEY")

VENUE_CAPACITY_TIERS = [200, 300, 400, 500, 750, 1000, 1500, 2000, 3000, 5000]
DAYS_UNTIL_EVENT_SCENARIOS = [1, 3, 5, 7, 10, 14, 21, 30, 45, 60, 90]

GENRE_MAP = {
    "electronic": 1, "techno": 2, "house": 3, "trance": 4,
    "drum and bass": 5, "dubstep": 6, "edm": 7, "dance": 8,
    "pop": 9, "rock": 10, "hip-hop": 11, "jazz": 12,
    "classical": 13, "metal": 14, "indie": 15, "other": 0,
}


def get_lastfm_top_artists_by_tag(tag, limit=50):
    """Dohvaća top izvođače za zadani žanr (tag) s Last.fm-a."""
    url = "https://ws.audioscrobbler.com/2.0/"
    params = {
        "method": "tag.gettopartists",
        "tag": tag,
        "api_key": LASTFM_KEY,
        "format": "json",
        "limit": limit,
    }
    response = requests.get(url, params=params, timeout=10)
    if response.status_code != 200:
        return []
    data = response.json()
    artists = data.get("topartists", {}).get("artist", [])
    return [a.get("name") for a in artists if a.get("name")]


def get_artist_full_data(artist_name, network):
    """Dohvaća listeners/playcount/tags za pojedinog izvođača."""
    try:
        artist = network.get_artist(artist_name)
        listeners = int(artist.get_listener_count() or 0)
        playcount = int(artist.get_playcount() or 0)
        top_tags = artist.get_top_tags(limit=3) or []
        tags = [t.item.name.lower() for t in top_tags]
        return {
            "artist_name": artist_name,
            "artist_listeners": listeners,
            "artist_playcount": playcount,
            "artist_tags": tags,
        }
    except Exception:
        return None


def calculate_base_price(artist_listeners, venue_capacity, days_until_event, genre_encoded):
    """Identična deterministička formula kao u pipeline_task.py."""
    if artist_listeners > 0:
        popularity_score = min(math.log10(artist_listeners) / 7.0, 1.0)
    else:
        popularity_score = 0.1

    if venue_capacity and venue_capacity > 0:
        capacity_factor = max(0.5, 1.0 - (venue_capacity / 10000) * 0.3)
    else:
        capacity_factor = 0.8

    if days_until_event <= 7:
        urgency_factor = 1.3
    elif days_until_event <= 30:
        urgency_factor = 1.1
    else:
        urgency_factor = 1.0

    genre_factor = 1.2 if genre_encoded in [1, 2, 3, 4, 5, 6, 7, 8] else 1.0

    base = 20 + (popularity_score * 130 * capacity_factor * genre_factor)
    return round(base * urgency_factor, 2)


def generate_training_records(artist_data, genre_encoded):
    """Iz jednog izvođača radi NxM zapisa kombinacijom kapaciteta i dana."""
    records = []
    for capacity in VENUE_CAPACITY_TIERS:
        for days_until in DAYS_UNTIL_EVENT_SCENARIOS:
            price = calculate_base_price(
                artist_data["artist_listeners"], capacity, days_until, genre_encoded
            )

            # Deterministički tickets_sold_ratio – ovisi samo o danima do eventa
            if days_until <= 7:
                tickets_sold_ratio = 0.85
            elif days_until <= 30:
                tickets_sold_ratio = 0.60
            else:
                tickets_sold_ratio = 0.30

            day_of_week = (capacity + days_until) % 7

            records.append({
                "artist_listeners": artist_data["artist_listeners"],
                "artist_playcount": artist_data["artist_playcount"],
                "genre_encoded": genre_encoded,
                "venue_capacity": capacity,
                "days_until_event": days_until,
                "tickets_sold_ratio": tickets_sold_ratio,
                "day_of_week": day_of_week,
                "optimal_price": price,
                "artist_name": artist_data["artist_name"],
                "generated_at": datetime.utcnow(),
                "source": "deterministic_generator",
            })
    return records


def run_generator():
    if not LASTFM_KEY:
        raise RuntimeError("LASTFM_API_KEY nije postavljen u env varijablama.")

    client = MongoClient("mongodb://mongo:27017")
    db = client["mydb"]
    network = pylast.LastFMNetwork(api_key=LASTFM_KEY)

    db.ml_training_data.drop()
    print("Stari training podaci očišćeni.")

    tags_to_fetch = [
        ("electronic", 1), ("techno", 2), ("house", 3),
        ("trance", 4), ("drum and bass", 5), ("pop", 9),
        ("rock", 10), ("hip-hop", 11), ("jazz", 12), ("indie", 15),
    ]

    total_records = 0
    all_artist_names = set()

    for tag, genre_code in tags_to_fetch:
        print(f"\nDohvaćanje top izvođača za žanr: {tag}")
        artist_names = get_lastfm_top_artists_by_tag(tag, limit=30)
        time.sleep(0.5)

        batch_records = []
        for artist_name in artist_names:
            if artist_name in all_artist_names:
                continue
            all_artist_names.add(artist_name)

            artist_data = get_artist_full_data(artist_name, network)
            time.sleep(0.3)

            if not artist_data or artist_data["artist_listeners"] == 0:
                continue

            records = generate_training_records(artist_data, genre_code)
            batch_records.extend(records)
            print(f"  {artist_name}: {artist_data['artist_listeners']:,} listenera -> {len(records)} zapisa")

        if batch_records:
            db.ml_training_data.insert_many(batch_records)
            total_records += len(batch_records)
            print(f"  Žanr '{tag}': upisano {len(batch_records)} zapisa")

    print(f"\nGenerator završen: ukupno {total_records} training zapisa")
    client.close()


if __name__ == "__main__":
    run_generator()
