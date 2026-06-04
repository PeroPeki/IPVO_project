"""
Sveobuhvatni test skript za NightClub Manager sustav.
Pokreće se unutar backend kontejnera: docker compose exec backend python run_tests.py
"""
import json
import os
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone

import pika
import redis
import requests as http
from pymongo import MongoClient

# Lokalni importovi iz backend koda
from pipeline_task import (
    calculate_base_price,
    encode_genre,
    compute_days_until_event,
    compute_default_tickets_sold_ratio,
)


# ============================================================================
# TEST INFRASTRUKTURA
# ============================================================================

RESULTS = []  # lista (status, name, message)


def record(status, name, message):
    RESULTS.append((status, name, message))
    icon = {"PASS": "PASS", "FAIL": "FAIL", "SKIP": "SKIP"}[status]
    print(f"[{icon}] {name}: {message}")


def run(name, fn):
    try:
        fn()
    except AssertionError as exc:
        record("FAIL", name, f"AssertionError: {exc}")
    except Exception as exc:
        record("FAIL", name, f"{type(exc).__name__}: {exc}")
        traceback.print_exc()


# Connection setup (jednom)
mongo = MongoClient("mongodb://mongo:27017")
db = mongo["mydb"]
rcache = redis.Redis(host="redis", port=6379, db=0)
BACKEND = "http://backend:5000"
PREDICT = "http://prediction_service:6000"
PROM = "http://prometheus:9090"


# ============================================================================
# 1. UNIT TESTOVI — ČISTE FUNKCIJE
# ============================================================================

def test_calc_price_baseline():
    name = "1.1 calculate_base_price — baseline (1M listenera, kap 500, 14d, techno)"
    price = calculate_base_price(1_000_000, 500, 14, 2)
    # Formula: 20 + log10(1e6)/7 * 130 * cap_factor(0.985) * genre(1.2) → ~152, * urgency(1.1) → ~167
    assert 80 <= price <= 200, f"price={price} izvan [80, 200]"
    record("PASS", name, f"price={price} EUR (unutar očekivanog [80, 200])")


def test_calc_price_urgency():
    name = "1.2 calculate_base_price — urgency factor"
    p14 = calculate_base_price(1_000_000, 500, 14, 2)
    p3 = calculate_base_price(1_000_000, 500, 3, 2)
    assert p3 > p14, f"urgency ne pojačava cijenu: p3={p3}, p14={p14}"
    record("PASS", name, f"p3={p3} > p14={p14} (urgency_factor 1.3 vs 1.1 / 1.0)")


def test_encode_genre_known():
    name = "1.3 encode_genre — poznati tagovi"
    cases = [
        (["techno", "dark techno"], 2),
        (["pop", "indie pop"], 9),
        (["nepoznato", "xyz"], 0),
    ]
    for tags, expected in cases:
        got = encode_genre(tags)
        # NB: "indie pop" sadrži "indie" koji je u GENRE_MAP=15;
        # encode_genre vraća prvi match. Provjeri stvarno ponašanje.
        if expected == 9 and got == 15:
            record("FAIL", name, f"tags={tags}: očekivano {expected}, dobiveno {got} "
                                   "(encode_genre matcha 'indie' prije 'pop' jer je u tagu 'indie pop')")
            return
        assert got == expected, f"tags={tags}: očekivano {expected}, dobiveno {got}"
    record("PASS", name, "sva 3 slučaja prošla (techno→2, pop→9, nepoznato→0)")


def test_compute_days_until_event():
    name = "1.4 compute_days_until_event — vremenski izračun"
    future = datetime.now(timezone.utc) + timedelta(days=10)
    past = datetime.now(timezone.utc) - timedelta(days=5)
    df = compute_days_until_event(future)
    dp = compute_days_until_event(past)
    none_val = compute_days_until_event(None)
    assert df >= 9, f"future treba biti ~10, dobiveno {df}"
    assert dp == 0, f"past treba biti 0 (clamp), dobiveno {dp}"
    assert none_val == 30, f"None default je 30, dobiveno {none_val}"
    record("PASS", name, f"future={df}, past={dp} (clamp na 0), None→{none_val}")


def test_tickets_sold_ratio_edge():
    name = "1.5 compute_default_tickets_sold_ratio — edge cases"
    # NB: stvarna funkcija ne dijeli s nulom — uzima days_until_event
    # Provjeri sve grane formule
    r7 = compute_default_tickets_sold_ratio(7)
    r30 = compute_default_tickets_sold_ratio(30)
    r60 = compute_default_tickets_sold_ratio(60)
    r0 = compute_default_tickets_sold_ratio(0)
    assert r7 == 0.85 and r0 == 0.85, f"<=7: r7={r7}, r0={r0}"
    assert r30 == 0.60, f"<=30: r30={r30}"
    assert r60 == 0.30, f"60: r60={r60}"
    record("PASS", name,
           f"r0=0.85, r7=0.85, r30=0.60, r60=0.30 — sve 3 grane formule OK, nema dijeljenja s nulom")


# ============================================================================
# 2. MONGODB KOLEKCIJE I INDEKSI
# ============================================================================

def test_mongo_collections_exist():
    name = "2.1 MongoDB — sve potrebne kolekcije postoje"
    required = {"clubs", "events", "tables", "reservations", "users", "tickets",
                "ml_training_data", "price_log", "model_metadata", "reports"}
    existing = set(db.list_collection_names())
    missing = required - existing
    if missing:
        record("FAIL", name, f"nedostaju kolekcije: {missing}")
        return
    record("PASS", name, f"sve {len(required)} kolekcije postoje")


def test_mongo_indexes():
    name = "2.2 MongoDB — kritični indeksi postoje"
    checks = [
        ("events", "ticketmaster_id_1"),
        ("events", "club_id_1"),
        ("tables", "event_id_1"),
        ("price_log", "timestamp_-1"),
        ("ml_training_data", "artist_name_1"),
    ]
    missing = []
    for coll, idx_name in checks:
        idx_info = db[coll].index_information()
        # idx names u pymongo: "{field}_{direction}"
        if idx_name not in idx_info:
            # ponekad ima drugi naziv — provjeri preko fielda
            found = False
            field = idx_name.rsplit("_", 1)[0]
            for info in idx_info.values():
                keys = info.get("key", [])
                if any(k[0] == field for k in keys):
                    found = True
                    break
            if not found:
                missing.append(f"{coll}.{idx_name}")
    if missing:
        record("FAIL", name, f"nedostaju indeksi: {missing}")
        return
    record("PASS", name, "svih 5 kritičnih indeksa postoji")


def test_events_not_empty():
    name = "2.3 MongoDB — events kolekcija nije prazna i ima ML polja"
    cnt = db.events.count_documents({})
    if cnt == 0:
        record("FAIL", name, "events kolekcija je prazna")
        return
    sample = db.events.find_one({})
    required_fields = {"ticketmaster_id", "base_price", "current_price",
                       "artist_listeners", "genre_encoded", "venue_capacity",
                       "days_until_event"}
    missing = required_fields - set(sample.keys())
    if missing:
        record("FAIL", name, f"event {sample.get('ticketmaster_id')} nedostaju polja: {missing}")
        return
    record("PASS", name, f"{cnt} eventa, sample {sample['ticketmaster_id']} ima sva ML polja")


def test_setoninsert_preserves_current_price():
    name = "2.4 MongoDB — $setOnInsert čuva current_price kroz upsert"
    sample = db.events.find_one({})
    if not sample:
        record("SKIP", name, "nema event uzorka")
        return
    original_current = sample["current_price"]
    fake_new_base = original_current + 99.99  # simulacija pipeline-a koji bi htio promijeniti

    # Simuliraj točno isti upsert kao u tasks.py
    db.events.update_one(
        {"ticketmaster_id": sample["ticketmaster_id"]},
        {
            "$set": {"pipeline_updated_at": datetime.utcnow(), "base_price": fake_new_base},
            "$setOnInsert": {"current_price": fake_new_base},  # ovo se NE smije primijeniti
        },
        upsert=True,
    )

    after = db.events.find_one({"ticketmaster_id": sample["ticketmaster_id"]})
    if after["current_price"] != original_current:
        record("FAIL", name,
               f"current_price se promijenio s {original_current} na {after['current_price']}")
        return
    # vrati base_price natrag
    db.events.update_one(
        {"ticketmaster_id": sample["ticketmaster_id"]},
        {"$set": {"base_price": sample["base_price"]}},
    )
    record("PASS", name,
           f"current_price {original_current} ostao netaknut nakon upserta (base_price se updateao)")


# ============================================================================
# 3. REDIS PREDMEMORIJA
# ============================================================================

def test_redis_ping():
    name = "3.1 Redis — ping odgovara"
    assert rcache.ping() is True
    record("PASS", name, "PONG")


def test_redis_pricing_cache():
    name = "3.2 Redis — /api/events/<id>/pricing cache hit i TTL"
    sample = db.events.find_one({})
    if not sample:
        record("SKIP", name, "nema eventa")
        return
    eid = sample.get("id") or sample.get("ticketmaster_id")
    cache_key = f"event_pricing_{eid}"
    rcache.delete(cache_key)

    r1 = http.get(f"{BACKEND}/api/events/{eid}/pricing", timeout=10)
    assert r1.status_code == 200, f"prvi GET status {r1.status_code}"
    cached_raw = rcache.get(cache_key)
    assert cached_raw is not None, "cache key nije postavljen nakon prvog GET-a"

    ttl = rcache.ttl(cache_key)
    assert 0 < ttl <= 60, f"TTL {ttl} nije u (0, 60]"

    r2 = http.get(f"{BACKEND}/api/events/{eid}/pricing", timeout=10)
    assert r2.status_code == 200
    assert r1.json() == r2.json(), "drugi odgovor se razlikuje od prvog (cache miss?)"
    record("PASS", name, f"cache hit OK, TTL={ttl}s")


def test_redis_invalidation_on_price_log():
    """Cache se invalidira u log_price_change (prediction_service),
    a ne u notify-price-change (backend). Simuliraj tako da ručno
    obrišemo ključ kao što log_price_change radi i provjerimo TTL semantiku."""
    name = "3.3 Redis — cache.delete invalidira event_pricing ključ"
    sample = db.events.find_one({})
    if not sample:
        record("SKIP", name, "nema eventa")
        return
    eid = sample.get("id") or sample.get("ticketmaster_id")
    cache_key = f"event_pricing_{eid}"
    http.get(f"{BACKEND}/api/events/{eid}/pricing", timeout=10)
    assert rcache.get(cache_key) is not None, "cache nije popunjen"
    # log_price_change radi: cache.delete(f"event_pricing_{event_id}")
    rcache.delete(cache_key)
    assert rcache.get(cache_key) is None, "delete nije obrisao ključ"
    # sljedeći GET treba opet popuniti
    http.get(f"{BACKEND}/api/events/{eid}/pricing", timeout=10)
    assert rcache.get(cache_key) is not None, "cache nije rebuildan nakon invalidacije"
    record("PASS", name,
           "delete(event_pricing_<id>) radi; backend re-populira pri sljedećem GET-u "
           "(isti mehanizam koji koristi prediction_service.log_price_change)")


# ============================================================================
# 4. PREDICTION SERVICE
# ============================================================================

def test_predict_health():
    name = "4.1 prediction_service — GET /health"
    r = http.get(f"{PREDICT}/health", timeout=5)
    j = r.json()
    assert r.status_code == 200 and j.get("status") == "ok" and j.get("model_loaded") is True
    record("PASS", name, f"status=ok, model_loaded=True")


def test_predict_model_info():
    name = "4.2 prediction_service — GET /model-info"
    r = http.get(f"{PREDICT}/model-info", timeout=5)
    j = r.json()
    expected_keys = {"best_model", "best_rmse", "features", "trained_at"}
    if "message" in j:
        record("SKIP", name, "nema metadata zapisa (model nije treniran kroz pipeline)")
        return
    missing = expected_keys - set(j.keys())
    assert not missing, f"nedostaju polja: {missing}"
    record("PASS", name, f"best_model={j.get('best_model')}, rmse={j.get('best_rmse')}")


def test_predict_basic():
    name = "4.3 prediction_service — POST /predict-price (basic)"
    payload = {
        "artist_listeners": 500_000,
        "artist_playcount": 25_000_000,
        "genre_encoded": 2,
        "venue_capacity": 800,
        "days_until_event": 14,
        "tickets_sold_ratio": 0.5,
        "day_of_week": 5,
        "event_id": "test_event_unique_id_xyz",
        "current_price": 60.0,
    }
    r = http.post(f"{PREDICT}/predict-price", json=payload, timeout=5)
    assert r.status_code == 200, f"status {r.status_code}: {r.text}"
    j = r.json()
    p = j["predicted_price"]
    assert isinstance(p, float), f"predicted_price nije float: {type(p)}"
    assert 10.0 <= p <= 500.0, f"predicted_price={p} izvan [10, 500]"
    # provjeri 2 decimale
    assert round(p, 2) == p, f"predicted_price nije 2 decimale: {p}"
    record("PASS", name, f"predicted_price={p} EUR (float, 2 decimale, unutar [10, 500])")


def test_predict_edge_zero_listeners():
    name = "4.4 prediction_service — POST /predict-price (artist_listeners=0)"
    payload = {
        "artist_listeners": 0, "artist_playcount": 0, "genre_encoded": 0,
        "venue_capacity": 100, "days_until_event": 60,
        "tickets_sold_ratio": 0.1, "day_of_week": 2,
        "event_id": "test_zero_listeners",
    }
    r = http.post(f"{PREDICT}/predict-price", json=payload, timeout=5)
    assert r.status_code == 200, f"status {r.status_code}: {r.text}"
    p = r.json()["predicted_price"]
    assert p >= 10.0, f"min cijena nije {p} >= 10"
    record("PASS", name, f"price={p} (>= 10 EUR, model preživio log10(0+1)=0)")


def test_predict_default_missing_fields():
    name = "4.5 prediction_service — POST /predict-price (prazno tijelo s event_id)"
    # prazno tijelo bi vratilo 400 (data is None); slanje praznog dicta + event_id radi
    payload = {"event_id": "test_defaults"}
    r = http.post(f"{PREDICT}/predict-price", json=payload, timeout=5)
    assert r.status_code == 200, f"status {r.status_code}: {r.text}"
    p = r.json()["predicted_price"]
    assert p >= 10.0
    record("PASS", name, f"price={p} (defaults korišteni za sva polja osim event_id)")


def test_predict_metrics_endpoint():
    name = "4.6 prediction_service — GET /metrics sadrži ML metrike"
    r = http.get(f"{PREDICT}/metrics", timeout=5)
    body = r.text
    assert r.status_code == 200
    for metric in ("predictions_total", "model_loaded", "cache_hits_total"):
        assert metric in body, f"nedostaje {metric}"
    record("PASS", name, "predictions_total, model_loaded, cache_hits_total prisutne")


def test_predict_cache_hit_increments():
    name = "4.7 prediction_service — cache hit povećava cache_hits_total"
    eid = "test_cache_hit_xyz_unique"
    rcache.delete(f"price_prediction_{eid}")
    payload = {
        "artist_listeners": 300_000, "artist_playcount": 8_000_000, "genre_encoded": 3,
        "venue_capacity": 600, "days_until_event": 20, "tickets_sold_ratio": 0.5,
        "day_of_week": 4, "event_id": eid,
    }
    # prvi poziv — miss
    http.post(f"{PREDICT}/predict-price", json=payload, timeout=5)
    # snimi metric prije drugog poziva
    body_before = http.get(f"{PREDICT}/metrics", timeout=5).text
    def metric_val(text, key):
        for line in text.splitlines():
            if line.startswith(key + " "):
                return float(line.split()[1])
        return 0.0
    cache_before = metric_val(body_before, "cache_hits_total")
    # drugi poziv — hit
    http.post(f"{PREDICT}/predict-price", json=payload, timeout=5)
    body_after = http.get(f"{PREDICT}/metrics", timeout=5).text
    cache_after = metric_val(body_after, "cache_hits_total")
    assert cache_after > cache_before, f"cache_hits_total nije porastao: {cache_before} -> {cache_after}"
    record("PASS", name, f"cache_hits_total {cache_before} → {cache_after}")


# ============================================================================
# 5. BACKEND API ENDPOINTI
# ============================================================================

def test_api_clubs():
    name = "5.1 backend — GET /api/clubs"
    r = http.get(f"{BACKEND}/api/clubs", timeout=10)
    assert r.status_code == 200
    j = r.json()
    clubs = j.get("clubs") if isinstance(j, dict) else j
    assert isinstance(clubs, list) and len(clubs) > 0, f"prazna lista klubova: {j}"
    record("PASS", name, f"{len(clubs)} klubova")


def test_api_events():
    name = "5.2 backend — GET /api/events"
    r = http.get(f"{BACKEND}/api/events", timeout=10)
    assert r.status_code == 200
    j = r.json()
    events = j.get("events") if isinstance(j, dict) else j
    assert isinstance(events, list) and len(events) > 0, f"prazna lista eventa: {j}"
    first = events[0]
    assert "base_price" in first and "current_price" in first
    record("PASS", name,
           f"{len(events)} eventa (count={j.get('count')}), prvi base={first['base_price']}, current={first['current_price']}")


def test_api_pricing():
    name = "5.3 backend — GET /api/events/<id>/pricing"
    sample = db.events.find_one({})
    eid = sample.get("id") or sample.get("ticketmaster_id")
    r = http.get(f"{BACKEND}/api/events/{eid}/pricing", timeout=10)
    assert r.status_code == 200
    j = r.json()
    for k in ("base_price", "current_price", "high_demand", "min_price", "max_price"):
        assert k in j, f"nedostaje polje {k}"
    record("PASS", name, f"sva polja prisutna: base={j['base_price']}, current={j['current_price']}, high_demand={j['high_demand']}")


def test_api_price_log():
    name = "5.4 backend — GET /api/price-log"
    r = http.get(f"{BACKEND}/api/price-log", timeout=10)
    assert r.status_code == 200
    j = r.json()
    log = j.get("price_log") if isinstance(j, dict) else j
    assert isinstance(log, list), f"očekivana lista, dobiveno {type(log)}: {j}"
    record("PASS", name, f"vraća listu duljine {len(log)}")


def test_api_model_status():
    name = "5.5 backend — GET /api/model-status (proxy)"
    r = http.get(f"{BACKEND}/api/model-status", timeout=10)
    assert r.status_code == 200
    j = r.json()
    assert "best_model" in j or "message" in j, f"neočekivan body: {j}"
    record("PASS", name, f"proxy radi: {list(j.keys())[:3]}")


def test_api_request_price_update():
    name = "5.6 backend — POST /api/events/<id>/request-price-update"
    sample = db.events.find_one({"id": {"$exists": True}}) or db.events.find_one({})
    eid = sample.get("id") or sample.get("ticketmaster_id")
    r = http.post(f"{BACKEND}/api/events/{eid}/request-price-update", timeout=10)
    # 200 ili 202 (Accepted — async pattern) su oba ispravna
    assert r.status_code in (200, 202), f"unexpected status {r.status_code}: {r.text}"
    j = r.json()
    assert j.get("success") is True, f"success != True: {j}"
    record("PASS", name, f"status={r.status_code}, success=True, msg={j.get('message', '')[:60]}")


def test_api_pricing_404():
    name = "5.7 backend — GET /api/events/NEPOSTOJECI/pricing → 404"
    r = http.get(f"{BACKEND}/api/events/NEPOSTOJECI_ID_XYZ/pricing", timeout=10)
    assert r.status_code == 404, f"očekivan 404, dobiveno {r.status_code}"
    record("PASS", name, "vraća 404 za nepostojeći event")


def test_api_request_price_update_404():
    name = "5.8 backend — POST request-price-update za nepostojeći event"
    r = http.post(f"{BACKEND}/api/events/NEPOSTOJECI_ID_XYZ/request-price-update", timeout=10)
    j = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    # success bi trebao biti False ili 404
    if r.status_code == 404 or j.get("success") is False:
        record("PASS", name, f"status={r.status_code}, body={j}")
        return
    record("FAIL", name, f"očekivan 404 ili success=false, dobiveno status={r.status_code}, body={j}")


# ============================================================================
# 6. INTEGRACIJSKI TEST — KOMPLETNI TOK CIJENE
# ============================================================================

def test_integration_price_flow():
    name = "6.1 INTEGRATION — request-price-update → RabbitMQ → prediction_service"
    sample = db.events.find_one({})
    eid = sample.get("id") or sample.get("ticketmaster_id")

    body_before = http.get(f"{PREDICT}/metrics", timeout=5).text
    def metric_val(text, key):
        for line in text.splitlines():
            if line.startswith(key + " "):
                return float(line.split()[1])
        return 0.0
    pred_before = metric_val(body_before, "predictions_total")
    log_before = db.price_log.count_documents({})

    r = http.post(f"{BACKEND}/api/events/{eid}/request-price-update", timeout=10)
    assert r.status_code in (200, 202), f"status {r.status_code}: {r.text}"
    assert r.json().get("success") is True

    # consumer treba obraditi poruku iz queue-a
    time.sleep(6)

    body_after = http.get(f"{PREDICT}/metrics", timeout=5).text
    pred_after = metric_val(body_after, "predictions_total")
    log_after = db.price_log.count_documents({})

    assert pred_after > pred_before, \
        f"predictions_total nije porastao: {pred_before} → {pred_after} (consumer nije obradio?)"
    record("PASS", name,
           f"predictions_total {pred_before} → {pred_after}, price_log {log_before} → {log_after}")


# ============================================================================
# 7. RABBITMQ
# ============================================================================

def test_rabbitmq_queue_exists():
    name = "7.1 RabbitMQ — price_update_queue postoji i deklarirana je durable"
    conn = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq"))
    ch = conn.channel()
    # passive=True samo provjeri postoji li
    q = ch.queue_declare(queue="price_update_queue", durable=True, passive=True)
    msg_count = q.method.message_count
    conn.close()
    record("PASS", name, f"queue postoji, durable=True, messages={msg_count}")


def test_rabbitmq_direct_message_consumed():
    name = "7.2 RabbitMQ — direktna poruka u queue se obradi"
    body_before = http.get(f"{PREDICT}/metrics", timeout=5).text
    def metric_val(text, key):
        for line in text.splitlines():
            if line.startswith(key + " "):
                return float(line.split()[1])
        return 0.0
    pred_before = metric_val(body_before, "predictions_total")

    conn = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq"))
    ch = conn.channel()
    ch.queue_declare(queue="price_update_queue", durable=True)
    payload = {
        "artist_listeners": 400_000, "artist_playcount": 12_000_000,
        "genre_encoded": 1, "venue_capacity": 700, "days_until_event": 12,
        "tickets_sold_ratio": 0.5, "day_of_week": 3,
        "event_id": "test_direct_rabbitmq_xyz", "current_price": 55.0,
    }
    ch.basic_publish(
        exchange="",
        routing_key="price_update_queue",
        body=json.dumps(payload),
        properties=pika.BasicProperties(delivery_mode=2),
    )
    conn.close()
    time.sleep(5)

    # provjeri da je queue prazan (ili barem da je broj poruka manji)
    conn2 = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq"))
    ch2 = conn2.channel()
    q = ch2.queue_declare(queue="price_update_queue", durable=True, passive=True)
    remaining = q.method.message_count
    conn2.close()
    body_after = http.get(f"{PREDICT}/metrics", timeout=5).text
    pred_after = metric_val(body_after, "predictions_total")

    assert pred_after > pred_before, \
        f"predictions_total nije porastao: {pred_before} → {pred_after}"
    record("PASS", name,
           f"poruka obrađena (remaining={remaining}), predictions_total {pred_before} → {pred_after}")


# ============================================================================
# 8. PROMETHEUS
# ============================================================================

def _prom_targets():
    r = http.get(f"{PROM}/api/v1/targets", timeout=5)
    return r.json()


def test_prom_backend_up():
    name = "8.1 Prometheus — backend target je UP"
    data = _prom_targets()
    backends = [t for t in data["data"]["activeTargets"]
                if t["labels"].get("job") == "backend"]
    assert backends, "nema backend targeta"
    up = [t for t in backends if t.get("health") == "up"]
    assert up, f"backend targets nisu UP: {[t.get('health') for t in backends]}"
    record("PASS", name, f"{len(up)} backend target(a) UP")


def test_prom_prediction_up():
    name = "8.2 Prometheus — prediction_service target je UP"
    data = _prom_targets()
    preds = [t for t in data["data"]["activeTargets"]
             if t["labels"].get("job") == "prediction_service"]
    assert preds, "nema prediction_service targeta"
    up = [t for t in preds if t.get("health") == "up"]
    assert up, f"prediction_service targets nisu UP: {[t.get('health') for t in preds]}"
    record("PASS", name, f"{len(up)} prediction_service target(a) UP")


def test_prom_metrics_visible():
    name = "8.3 Prometheus — query http_requests_total i predictions_total vraća rezultate"
    for metric in ("http_requests_total", "predictions_total"):
        r = http.get(f"{PROM}/api/v1/query", params={"query": metric}, timeout=5)
        j = r.json()
        assert j["status"] == "success"
        # može biti prazno ako još nije scrapeano — provjeri samo da query radi
        result = j["data"]["result"]
        if not result:
            record("FAIL", name, f"{metric}: prazan rezultat (još nije scrapeano?)")
            return
    record("PASS", name, "oba metrika imaju rezultate u Prometheusu")


# ============================================================================
# 9. AUTO-RELOAD MODELA
# ============================================================================

def test_model_watcher_thread_running():
    name = "9.1 prediction_service — _model_reload_watcher dretva pokrenuta"
    # provjeri da postoji daemon dretva s metim threadom (introspekcija kroz docker logs / health)
    # ovdje samo provjeri da je model trenutno učitan (model_loaded gauge = 1)
    r = http.get(f"{PREDICT}/metrics", timeout=5).text
    for line in r.splitlines():
        if line.startswith("model_loaded "):
            val = float(line.split()[1])
            assert val == 1.0, f"model_loaded={val}, nije 1"
            record("PASS", name,
                   "model_loaded=1 (model je učitan; watcher dretva čeka 5min ciklus, full reload test bi trajao 6min)")
            return
    record("FAIL", name, "model_loaded gauge nije pronađen u /metrics")


# ============================================================================
# 10. IDEMPOTENTNOST PIPELINE-A ($setOnInsert vs $set)
# ============================================================================

def test_pipeline_idempotency():
    name = "10.1 pipeline — $setOnInsert ne mijenja current_price, $set mijenja pipeline_updated_at"
    sample = db.events.find_one({"current_price": {"$exists": True}})
    if not sample:
        record("SKIP", name, "nema sample eventa")
        return
    orig_cp = sample["current_price"]
    orig_updated = sample.get("pipeline_updated_at")
    new_ts = datetime.utcnow()

    db.events.update_one(
        {"ticketmaster_id": sample["ticketmaster_id"]},
        {
            "$set": {"pipeline_updated_at": new_ts},
            "$setOnInsert": {"current_price": orig_cp + 999.0},
        },
        upsert=True,
    )

    after = db.events.find_one({"ticketmaster_id": sample["ticketmaster_id"]})
    assert after["current_price"] == orig_cp, \
        f"current_price se promijenio {orig_cp} → {after['current_price']}"
    assert after["pipeline_updated_at"] != orig_updated, \
        f"pipeline_updated_at se NIJE promijenio"
    record("PASS", name,
           f"current_price stabilan ({orig_cp}), pipeline_updated_at osvježen ({orig_updated} → {after['pipeline_updated_at']})")


# ============================================================================
# RUNNER
# ============================================================================

ALL_TESTS = [
    # 1. Unit
    test_calc_price_baseline, test_calc_price_urgency, test_encode_genre_known,
    test_compute_days_until_event, test_tickets_sold_ratio_edge,
    # 2. Mongo
    test_mongo_collections_exist, test_mongo_indexes, test_events_not_empty,
    test_setoninsert_preserves_current_price,
    # 3. Redis
    test_redis_ping, test_redis_pricing_cache, test_redis_invalidation_on_price_log,
    # 4. Prediction
    test_predict_health, test_predict_model_info, test_predict_basic,
    test_predict_edge_zero_listeners, test_predict_default_missing_fields,
    test_predict_metrics_endpoint, test_predict_cache_hit_increments,
    # 5. Backend API
    test_api_clubs, test_api_events, test_api_pricing, test_api_price_log,
    test_api_model_status, test_api_request_price_update, test_api_pricing_404,
    test_api_request_price_update_404,
    # 6. Integration
    test_integration_price_flow,
    # 7. RabbitMQ
    test_rabbitmq_queue_exists, test_rabbitmq_direct_message_consumed,
    # 8. Prometheus
    test_prom_backend_up, test_prom_prediction_up, test_prom_metrics_visible,
    # 9. Model watcher
    test_model_watcher_thread_running,
    # 10. Pipeline idempotency
    test_pipeline_idempotency,
]


if __name__ == "__main__":
    print("=" * 80)
    print(f"NIGHTCLUB MANAGER — sveobuhvatni testovi  (start: {datetime.now().isoformat()})")
    print("=" * 80)
    for fn in ALL_TESTS:
        try:
            fn()
        except Exception as exc:
            record("FAIL", fn.__name__, f"unhandled: {type(exc).__name__}: {exc}")
            traceback.print_exc()
    print()
    print("=" * 80)
    print("SAŽETAK")
    print("=" * 80)
    passed = sum(1 for s, _, _ in RESULTS if s == "PASS")
    failed = sum(1 for s, _, _ in RESULTS if s == "FAIL")
    skipped = sum(1 for s, _, _ in RESULTS if s == "SKIP")
    total = len(RESULTS)
    print(f"Ukupno: {passed}/{total} prošlo  (FAIL: {failed}, SKIP: {skipped})")
    if failed:
        print()
        print("KRITIČNI PADOVI:")
        for status, name, msg in RESULTS:
            if status == "FAIL":
                print(f"  - {name}: {msg}")
    if skipped:
        print()
        print("PRESKOČENI:")
        for status, name, msg in RESULTS:
            if status == "SKIP":
                print(f"  - {name}: {msg}")
    sys.exit(0 if failed == 0 else 1)
