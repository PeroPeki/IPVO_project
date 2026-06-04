from gevent import monkey
monkey.patch_all()

"""
Prediction Service – Faza 4
- REST endpoint POST /predict-price
- RabbitMQ consumer (price_update_queue) u zasebnoj dretvi
- Redis cache za predikcije (TTL 5 min)
- Logiranje promjena cijena u MongoDB kolekciju price_log
"""

import json
import math
import os
import threading
import time
from datetime import datetime

import joblib
import numpy as np
import pika
import redis
import requests
from bson import ObjectId
from flask import Flask, jsonify, request, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from pymongo import MongoClient


app = Flask(__name__)

# =========================
# PROMETHEUS METRIKE
# =========================

predictions_total = Counter(
    'predictions_total',
    'Ukupan broj ML predikcija cijena'
)
price_changes_total = Counter(
    'price_changes_total',
    'Broj promjena cijena (razlika > 5 EUR)'
)
prediction_duration_seconds = Histogram(
    'prediction_duration_seconds',
    'Trajanje ML predikcije u sekundama'
)
model_loaded = Gauge(
    'model_loaded',
    'Je li ML model trenutno učitan (1=da, 0=ne)'
)
cache_hits_total = Counter(
    'cache_hits_total',
    'Broj Redis cache pogodaka pri predikciji'
)

MODEL_PATH = "/app/models/pricing_model.pkl"
FEATURES_PATH = "/app/models/feature_cols.pkl"

_model_lock = threading.Lock()

try:
    model = joblib.load(MODEL_PATH)
    feature_cols = joblib.load(FEATURES_PATH)
    _model_mtime = os.path.getmtime(MODEL_PATH)
    model_loaded.set(1)
    print(f"Model učitan. Featureovi: {feature_cols}")
except FileNotFoundError:
    print("UPOZORENJE: Model nije pronađen. Pokrenite train_model.py prvo.")
    model = None
    feature_cols = []
    _model_mtime = 0.0
    model_loaded.set(0)

cache = redis.Redis(host="redis", port=6379, db=0)

# Globalna MongoDB konekcija s connection poolom
mongo_client = MongoClient("mongodb://mongo:27017", maxPoolSize=10)
db = mongo_client["mydb"]


def prepare_input(data, cols=None):
    """Iz dolaznog JSON-a slaže feature vektor u redoslijedu kakav model očekuje."""
    if cols is None:
        cols = feature_cols
    listeners = data.get("artist_listeners", 100000)
    playcount = data.get("artist_playcount", 1000000)
    features = {
        "log_listeners": math.log10(listeners + 1),
        "log_playcount": math.log10(playcount + 1),
        "genre_encoded": data.get("genre_encoded", 0),
        "venue_capacity": data.get("venue_capacity", 500),
        "days_until_event": data.get("days_until_event", 30),
        "tickets_sold_ratio": data.get("tickets_sold_ratio", 0.5),
        "day_of_week": data.get("day_of_week", 5),
    }
    return np.array([[features[col] for col in cols]])


def _notify_backend_price_change(event_id, new_price):
    """Šalje backendu notifikaciju da emitira price_updated socket event."""
    try:
        # Dohvati base_price iz baze za high_demand izračun
        event_doc = db.events.find_one(
            {"$or": [{"id": event_id}, {"ticketmaster_id": event_id}]},
            {"base_price": 1},
        )
        base_price = (event_doc or {}).get("base_price") or new_price
        requests.post(
            f"http://backend:5000/api/events/{event_id}/notify-price-change",
            json={"new_price": new_price, "base_price": base_price},
            timeout=3,
        )
    except Exception as exc:
        print(f"Notify backend greška: {exc}")


def log_price_change(event_id, old_price, new_price):
    """Sprema promjenu cijene u price_log i ažurira current_price na eventu."""
    price_changes_total.inc()
    try:
        db.price_log.insert_one({
            "event_id": event_id,
            "timestamp": datetime.utcnow(),
            "old_price": old_price,
            "new_price": new_price,
            "reason": "ML model dynamic pricing update",
        })

        updated = False
        try:
            res = db.events.update_one(
                {"_id": ObjectId(event_id)},
                {"$set": {"current_price": new_price}},
            )
            updated = res.modified_count > 0
        except Exception:
            updated = False

        if not updated:
            db.events.update_one(
                {"$or": [{"id": event_id}, {"ticketmaster_id": event_id}]},
                {"$set": {"current_price": new_price}},
            )

        cache.delete(f"event_pricing_{event_id}")

        # Obavijesti backend da emitira WebSocket event klijentima
        _notify_backend_price_change(event_id, new_price)
    except Exception as exc:
        print(f"Greška pri unosu u price_log: {exc}")


@app.route("/predict-price", methods=["POST"])
def predict_price():
    with _model_lock:
        current_model = model
        current_features = feature_cols

    if current_model is None:
        return jsonify({"error": "Model nije učitan"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Potrebni su podaci o eventu"}), 400

    event_id = data.get("event_id")
    cache_key = f"price_prediction_{event_id}" if event_id else None

    if cache_key:
        cached = cache.get(cache_key)
        if cached:
            cache_hits_total.inc()
            return jsonify(json.loads(cached))

    predictions_total.inc()
    with prediction_duration_seconds.time():
        predicted_price = round(max(10.0, float(current_model.predict(prepare_input(data, current_features))[0])), 2)

    result = {
        "predicted_price": predicted_price,
        "event_id": event_id,
        "timestamp": datetime.utcnow().isoformat(),
        "model_version": "v1",
    }

    if cache_key:
        cache.setex(cache_key, 300, json.dumps(result))

    if event_id and data.get("current_price"):
        if abs(predicted_price - float(data["current_price"])) > 5.0:
            log_price_change(event_id, float(data["current_price"]), predicted_price)

    return jsonify(result)


@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model_loaded": model is not None})


@app.route("/model-info", methods=["GET"])
def model_info():
    try:
        meta = db.model_metadata.find_one({}, sort=[("trained_at", -1)])
        if meta:
            meta["_id"] = str(meta["_id"])
            if isinstance(meta.get("trained_at"), datetime):
                meta["trained_at"] = meta["trained_at"].isoformat()
        return jsonify(meta or {"message": "Nema podataka o modelu"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


def consume_price_requests():
    """RabbitMQ consumer s automatskim reconnectom u pozadinskoj dretvi."""
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host="rabbitmq",
                    heartbeat=600,
                    blocked_connection_timeout=300,
                )
            )
            channel = connection.channel()
            channel.queue_declare(queue="price_update_queue", durable=True)
            channel.basic_qos(prefetch_count=1)

            def callback(ch, method, properties, body):
                try:
                    with _model_lock:
                        cb_model = model
                        cb_features = feature_cols
                    if cb_model is None:
                        print("Consumer: model nije učitan, requeueam poruku.")
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                        time.sleep(30)
                        return
                    data = json.loads(body)
                    predictions_total.inc()
                    with prediction_duration_seconds.time():
                        predicted_price = round(
                            max(10.0, float(cb_model.predict(prepare_input(data, cb_features))[0])), 2
                        )
                    event_id = data.get("event_id")
                    current_price = float(data.get("current_price", predicted_price))
                    if event_id and abs(predicted_price - current_price) > 5.0:
                        log_price_change(event_id, current_price, predicted_price)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except (json.JSONDecodeError, ValueError) as exc:
                    # Pokvarena poruka — odbaci bez requeuea da ne kruži beskonačno
                    print(f"Consumer: neispravna poruka, odbacujem: {exc}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                except Exception as exc:
                    print(f"Consumer greška pri obradi poruke: {exc}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

            channel.basic_consume(
                queue="price_update_queue", on_message_callback=callback
            )
            print("Prediction Service consumer aktivan na queueu 'price_update_queue'")
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as exc:
            print(f"RabbitMQ nedostupan, pokušavam za 10s: {exc}")
            time.sleep(10)
        except Exception as exc:
            print(f"Consumer neočekivana greška, restart za 5s: {exc}")
            time.sleep(5)


def _model_reload_watcher():
    """Svakih 5 minuta provjerava je li pricing_model.pkl noviji od učitanog i ako da, reučitava."""
    global model, feature_cols, _model_mtime
    while True:
        time.sleep(300)
        try:
            current_mtime = os.path.getmtime(MODEL_PATH)
            if current_mtime > _model_mtime:
                new_model = joblib.load(MODEL_PATH)
                new_features = joblib.load(FEATURES_PATH)
                with _model_lock:
                    model = new_model
                    feature_cols = new_features
                    _model_mtime = current_mtime
                model_loaded.set(1)
                print(f"[model-watcher] Model reučitan (mtime: {current_mtime}). Featureovi: {feature_cols}")
        except FileNotFoundError:
            pass
        except Exception as exc:
            print(f"[model-watcher] Greška pri reučitavanju: {exc}")


if __name__ == "__main__":
    threading.Thread(target=consume_price_requests, daemon=True).start()
    threading.Thread(target=_model_reload_watcher, daemon=True).start()
    app.run(host="0.0.0.0", port=6000, debug=False)
