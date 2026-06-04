"""
Data Pipeline – Faza 4 (Global)
- Dohvat stvarnih glazbenih evenata s Ticketmaster Discovery API-ja za globalne gradove
- Obogaćivanje podataka putem Last.fm API-ja (listeners, playcount, tags)
- Deterministička formula za izračun bazne cijene stola
"""

import os
import math
import re
import time
import unicodedata
from datetime import datetime, timedelta, timezone

import requests
import pylast


TICKETMASTER_KEY = os.environ.get("TICKETMASTER_API_KEY")
LASTFM_KEY = os.environ.get("LASTFM_API_KEY")

# Globalna pokrivenost – Europa, Sjeverna Amerika, Australija.
# Ticketmaster Discovery API ima najjaču pokrivenost u tim regijama.
TARGET_CITIES = [
    # Europa
    ("Zagreb", "HR"), ("London", "GB"), ("Berlin", "DE"),
    ("Amsterdam", "NL"), ("Barcelona", "ES"), ("Paris", "FR"),
    ("Madrid", "ES"), ("Milan", "IT"), ("Vienna", "AT"),
    ("Prague", "CZ"),
    # Sjeverna Amerika
    ("New York", "US"), ("Los Angeles", "US"), ("Chicago", "US"),
    ("Miami", "US"), ("Las Vegas", "US"), ("Boston", "US"),
    ("Atlanta", "US"), ("Toronto", "CA"),
    # Australija
    ("Sydney", "AU"), ("Melbourne", "AU"),
]

DEFAULT_VENUE_CAPACITY = 1000

GENRE_MAP = {
    "electronic": 1, "techno": 2, "house": 3, "trance": 4,
    "drum and bass": 5, "dubstep": 6, "edm": 7, "dance": 8,
    "pop": 9, "rock": 10, "hip-hop": 11, "jazz": 12,
    "classical": 13, "metal": 14, "indie": 15, "other": 0,
}


def slugify(text):
    """ASCII-safe slug za korištenje kao stabilan id (npr. club_id)."""
    if not text:
        return "unknown"
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "unknown"


def _pick_best_image(images):
    """Iz Ticketmaster `images` polja vraća najveću sliku (ili None)."""
    if not images:
        return None
    sorted_imgs = sorted(
        images,
        key=lambda x: (x.get("width") or 0) * (x.get("height") or 0),
        reverse=True,
    )
    return sorted_imgs[0].get("url") if sorted_imgs else None


def _extract_price_range(event):
    """Iz `priceRanges` polja vraća min/max cijenu (ili None)."""
    price_ranges = event.get("priceRanges") or []
    if not price_ranges:
        return None, None
    pr = price_ranges[0]
    return pr.get("min"), pr.get("max")


def _extract_genre_from_classifications(event):
    """Pokušaj izvući žanr iz `classifications` polja (TM segment/genre)."""
    classifications = event.get("classifications") or []
    if not classifications:
        return None
    c = classifications[0]
    parts = []
    for key in ("genre", "subGenre", "segment"):
        node = c.get(key)
        if node and node.get("name") and node["name"].lower() != "undefined":
            parts.append(node["name"])
    return ", ".join(parts) if parts else None


def _parse_events(raw_events, city, country_code):
    """Parsira sirove TM evente u našu strukturu."""
    parsed = []
    for event in raw_events:
        try:
            attractions = event.get("_embedded", {}).get("attractions", []) or []
            artist_name = attractions[0]["name"] if attractions else event.get("name", "Unknown")

            venues = event.get("_embedded", {}).get("venues", []) or []
            venue = venues[0] if venues else {}
            venue_id = venue.get("id")
            venue_name = venue.get("name", "Unknown")
            venue_capacity = venue.get("capacity")
            venue_city = (venue.get("city") or {}).get("name") or city
            venue_country = (venue.get("country") or {}).get("countryCode") or country_code
            venue_country_name = (venue.get("country") or {}).get("name")
            venue_address = (venue.get("address") or {}).get("line1")
            venue_postal = venue.get("postalCode")
            venue_url = venue.get("url")
            venue_lat = (venue.get("location") or {}).get("latitude")
            venue_lon = (venue.get("location") or {}).get("longitude")

            event_date_str = event.get("dates", {}).get("start", {}).get("dateTime")
            event_date_local = event.get("dates", {}).get("start", {}).get("localDate")
            event_time_local = event.get("dates", {}).get("start", {}).get("localTime")
            try:
                event_date = (
                    datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))
                    if event_date_str else None
                )
            except Exception:
                event_date = None

            tm_min, tm_max = _extract_price_range(event)
            tm_genre = _extract_genre_from_classifications(event)
            image_url = _pick_best_image(event.get("images"))
            info = event.get("info") or event.get("pleaseNote") or ""

            parsed.append({
                "ticketmaster_id": event.get("id"),
                "name": event.get("name"),
                "artist_name": artist_name,
                "city": venue_city,
                "country": venue_country,
                "country_name": venue_country_name,
                "venue_id": venue_id,
                "venue_name": venue_name,
                "venue_capacity": venue_capacity,
                "venue_address": venue_address,
                "venue_postal_code": venue_postal,
                "venue_url": venue_url,
                "venue_latitude": venue_lat,
                "venue_longitude": venue_lon,
                "event_date": event_date,
                "event_date_local": event_date_local,
                "event_time_local": event_time_local,
                "url": event.get("url"),
                "image_url": image_url,
                "info": info,
                "tm_genre": tm_genre,
                "tm_min_price": tm_min,
                "tm_max_price": tm_max,
            })
        except Exception as exc:
            print(f"Greška pri parsiranju eventa: {exc}")
            continue
    return parsed


def fetch_ticketmaster_events(city, country_code, max_pages=3):
    """Dohvaća glazbene evente za zadani grad u idućih 90 dana — s paginacijom (do 60 eventa)."""
    if not TICKETMASTER_KEY:
        print("TICKETMASTER_API_KEY nije postavljen – preskačem dohvat.")
        return []

    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    all_events = []

    for page in range(max_pages):
        params = {
            "apikey": TICKETMASTER_KEY,
            "city": city,
            "countryCode": country_code,
            "classificationName": "music",
            "size": 20,
            "page": page,
            "sort": "date,asc",
            "startDateTime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "endDateTime": (datetime.utcnow() + timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        try:
            response = requests.get(url, params=params, timeout=15)
        except requests.RequestException as exc:
            print(f"Ticketmaster mrežna greška za {city} stranica {page}: {exc}")
            break

        if response.status_code != 200:
            print(
                f"Ticketmaster greška za {city} stranica {page}: "
                f"{response.status_code} – {response.text[:200]}"
            )
            break

        data = response.json()
        if "_embedded" not in data or "events" not in data["_embedded"]:
            break

        all_events.extend(_parse_events(data["_embedded"]["events"], city, country_code))

        total_pages = data.get("page", {}).get("totalPages", 1)
        if page + 1 >= total_pages:
            break

        time.sleep(0.5)

    return all_events


def get_lastfm_artist_data(artist_name, network=None):
    """Obogaćuje izvođača podacima s Last.fm API-ja. Network se može proslijediti za reuse."""
    if not LASTFM_KEY:
        return {"artist_listeners": 0, "artist_playcount": 0, "artist_tags": []}
    try:
        if network is None:
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


def compute_day_of_week(event_date):
    """Vraća dan u tjednu (0=ponedjeljak ... 6=nedjelja)."""
    if not event_date:
        return datetime.utcnow().weekday()
    return event_date.weekday()


def compute_default_tickets_sold_ratio(days_until_event):
    """
    Deterministički udio rasprodanosti ovisno o blizini eventa.
    Mora biti identičan onome u generate_training_data.py.
    """
    if days_until_event <= 7:
        return 0.85
    if days_until_event <= 30:
        return 0.60
    return 0.30
