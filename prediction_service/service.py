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
from datetime import datetime

import joblib
import numpy as np
import pika
import redis
from bson import ObjectId
from flask import Flask, jsonify, request
from pymongo import MongoClient


app = Flask(__name__)

MODEL_PATH = "/app/models/pricing_model.pkl"
FEATURES_PATH = "/app/models/feature_cols.pkl"

try:
    model = joblib.load(MODEL_PATH)
    feature_cols = joblib.load(FEATURES_PATH)
    print(f"Model učitan. Featureovi: {feature_cols}")
except FileNotFoundError:
    print("UPOZORENJE: Model nije pronađen. Pokrenite train_model.py prvo.")
    model = None
    feature_cols = []

cache = redis.Redis(host="redis", port=6379, db=0)


def prepare_input(data):
    """Iz dolaznog JSON-a slaže feature vektor u redoslijedu kakav model očekuje."""
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
    return np.array([[features[col] for col in feature_cols]])


def log_price_change(event_id, old_price, new_price):
    """Sprema promjenu cijene u price_log i ažurira current_price na eventu."""
    try:
        client = MongoClient("mongodb://mongo:27017")
        db = client["mydb"]
        db.price_log.insert_one({
            "event_id": event_id,
            "timestamp": datetime.utcnow(),
            "old_price": old_price,
            "new_price": new_price,
            "reason": "ML model dynamic pricing update",
        })
        try:
            db.events.update_one(
                {"_id": ObjectId(event_id)},
                {"$set": {"current_price": new_price}},
            )
        except Exception:
            db.events.update_one(
                {"id": event_id},
                {"$set": {"current_price": new_price}},
            )
        client.close()
    except Exception as exc:
        print(f"Greška pri unosu u price_log: {exc}")


@app.route("/predict-price", methods=["POST"])
def predict_price():
    if model is None:
        return jsonify({"error": "Model nije učitan"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Potrebni su podaci o eventu"}), 400

    event_id = data.get("event_id")
    cache_key = f"price_prediction_{event_id}" if event_id else None

    if cache_key:
        cached = cache.get(cache_key)
        if cached:
            return jsonify(json.loads(cached))

    predicted_price = round(max(10.0, float(model.predict(prepare_input(data))[0])), 2)

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


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model_loaded": model is not None})


@app.route("/model-info", methods=["GET"])
def model_info():
    try:
        client = MongoClient("mongodb://mongo:27017")
        meta = client["mydb"].model_metadata.find_one({}, sort=[("trained_at", -1)])
        client.close()
        if meta:
            meta["_id"] = str(meta["_id"])
            if isinstance(meta.get("trained_at"), datetime):
                meta["trained_at"] = meta["trained_at"].isoformat()
        return jsonify(meta or {"message": "Nema podataka o modelu"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


def consume_price_requests():
    """RabbitMQ consumer u pozadinskoj dretvi."""
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host="rabbitmq")
        )
        channel = connection.channel()
        channel.queue_declare(queue="price_update_queue", durable=True)

        def callback(ch, method, properties, body):
            try:
                data = json.loads(body)
                predicted_price = round(
                    max(10.0, float(model.predict(prepare_input(data))[0])), 2
                )
                event_id = data.get("event_id")
                current_price = float(data.get("current_price", predicted_price))
                if event_id and abs(predicted_price - current_price) > 5.0:
                    log_price_change(event_id, current_price, predicted_price)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as exc:
                print(f"Consumer greška: {exc}")
                ch.basic_nack(delivery_tag=method.delivery_tag)

        channel.basic_consume(
            queue="price_update_queue", on_message_callback=callback
        )
        print("Prediction Service consumer aktivan na queueu 'price_update_queue'")
        channel.start_consuming()
    except Exception as exc:
        print(f"RabbitMQ consumer greška: {exc}")


if __name__ == "__main__":
    if model is not None:
        threading.Thread(target=consume_price_requests, daemon=True).start()
    app.run(host="0.0.0.0", port=6000, debug=False)
