"""
Data Pipeline – Faza 4
- Dohvat stvarnih glazbenih evenata s Ticketmaster Discovery API-ja
- Obogaćivanje podataka putem Last.fm API-ja (listeners, playcount, tags)
- Deterministička formula za izračun bazne cijene stola
"""

import os
import math
from datetime import datetime, timedelta, timezone

import requests
import pylast


TICKETMASTER_KEY = os.environ.get("TICKETMASTER_API_KEY")
LASTFM_KEY = os.environ.get("LASTFM_API_KEY")

TARGET_CITIES = [
    ("London", "GB"), ("Berlin", "DE"), ("Amsterdam", "NL"),
    ("Barcelona", "ES"), ("Paris", "FR"), ("Milan", "IT"),
    ("Vienna", "AT"), ("Prague", "CZ"), ("Budapest", "HU"),
    ("Zagreb", "HR")
]

GENRE_MAP = {
    "electronic": 1, "techno": 2, "house": 3, "trance": 4,
    "drum and bass": 5, "dubstep": 6, "edm": 7, "dance": 8,
    "pop": 9, "rock": 10, "hip-hop": 11, "jazz": 12,
    "classical": 13, "metal": 14, "indie": 15, "other": 0,
}


def fetch_ticketmaster_events(city, country_code):
    """Dohvaća glazbene evente za zadani grad u idućih 90 dana."""
    if not TICKETMASTER_KEY:
        print("TICKETMASTER_API_KEY nije postavljen – preskačem dohvat.")
        return []

    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    params = {
        "apikey": TICKETMASTER_KEY,
        "city": city,
        "countryCode": country_code,
        "classificationName": "music",
        "size": 20,
        "sort": "date,asc",
        "startDateTime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endDateTime": (datetime.utcnow() + timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    try:
        response = requests.get(url, params=params, timeout=10)
    except requests.RequestException as exc:
        print(f"Ticketmaster mrežna greška za {city}: {exc}")
        return []

    if response.status_code != 200:
        print(f"Ticketmaster greška za {city}: {response.status_code}")
        return []

    data = response.json()
    if "_embedded" not in data or "events" not in data["_embedded"]:
        return []

    events = []
    for event in data["_embedded"]["events"]:
        try:
            attractions = event.get("_embedded", {}).get("attractions", [])
            artist_name = attractions[0]["name"] if attractions else event.get("name", "Unknown")

            venues = event.get("_embedded", {}).get("venues", [])
            venue_name = venues[0].get("name", "Unknown") if venues else "Unknown"
            venue_capacity = venues[0].get("capacity") if venues else None

            event_date_str = event.get("dates", {}).get("start", {}).get("dateTime")
            event_date = (
                datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))
                if event_date_str else None
            )

            events.append({
                "ticketmaster_id": event.get("id"),
                "name": event.get("name"),
                "artist_name": artist_name,
                "city": city,
                "country": country_code,
                "venue_name": venue_name,
                "venue_capacity": venue_capacity,
                "event_date": event_date,
                "url": event.get("url"),
            })
        except Exception as exc:
            print(f"Greška pri parsiranju eventa: {exc}")
            continue

    return events


def get_lastfm_artist_data(artist_name):
    """Obogaćuje izvođača podacima s Last.fm API-ja."""
    if not LASTFM_KEY:
        return {"artist_listeners": 0, "artist_playcount": 0, "artist_tags": []}
    try:
        network = pylast.LastFMNetwork(api_key=LASTFM_KEY)
        artist = network.get_artist(artist_name)
        playcount = int(artist.get_playcount() or 0)
        listeners = int(artist.get_listener_count() or 0)
        top_tags = artist.get_top_tags(limit=3) or []
        tags = [tag.item.name.lower() for tag in top_tags]
        return {
            "artist_listeners": listeners,
            "artist_playcount": playcount,
            "artist_tags": tags,
        }
    except Exception as exc:
        print(f"Last.fm greška za '{artist_name}': {exc}")
        return {"artist_listeners": 0, "artist_playcount": 0, "artist_tags": []}


def encode_genre(tags):
    """Mapira listu tagova u brojčani žanr kod."""
    for tag in tags:
        for genre_key in GENRE_MAP:
            if genre_key in tag:
                return GENRE_MAP[genre_key]
    return 0


def calculate_base_price(artist_listeners, venue_capacity, days_until_event, genre_encoded):
    """
    Deterministička pricing formula – isti ulazi uvijek daju isti izlaz.
    Mora biti identična onoj u generate_training_data.py.
    """
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
    price = base * urgency_factor
    return round(price, 2)


def compute_days_until_event(event_date):
    """Vraća broj dana do eventa, robusno na timezone."""
    if not event_date:
        return 30
    now = datetime.now(timezone.utc) if event_date.tzinfo else datetime.utcnow()
    return max(0, (event_date - now).days)
