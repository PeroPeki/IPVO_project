from gevent import monkey
monkey.patch_all()

from flask import Flask, jsonify, request, session, Response, g
from flask_socketio import SocketIO
from pymongo import MongoClient
from datetime import datetime
import pika
import json
import threading
import time
import redis

# =========================
# PROMETHEUS
# =========================
from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST
)

# =========================
# FLASK APP
# =========================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

cache = redis.Redis(host='redis', port=6379, db=0)

# =========================
# PROMETHEUS METRIKE
# =========================

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["endpoint"]
)

# =========================
# PROMETHEUS MIDDLEWARE
# =========================

@app.before_request
def start_timer():
    g.start_time = time.time()

@app.after_request
def record_metrics(response):
    # Preskoči metrics i websocket promet
    if request.path.startswith("/metrics") or request.path.startswith("/socket.io"):
        return response

    latency = time.time() - g.start_time
    endpoint = request.path

    REQUEST_LATENCY.labels(endpoint=endpoint).observe(latency)
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=endpoint,
        status=response.status_code
    ).inc()

    return response

@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

# =========================
# MONGO
# =========================

client = MongoClient("mongodb://mongo:27017", connect=False)
db = client["mydb"]

clubs_col = db["clubs"]
events_col = db["events"]
tables_col = db["tables"]
reservations_col = db["reservations"]
users_col = db["users"]
tickets_col = db["tickets"]

# =========================
# RABBITMQ
# =========================

def get_rabbitmq_connection():
    retries = 10
    while retries > 0:
        try:
            credentials = pika.PlainCredentials('guest', 'guest')
            parameters = pika.ConnectionParameters(
                host='rabbitmq',
                port=5672,
                credentials=credentials,
                connection_attempts=5,
                retry_delay=2
            )
            return pika.BlockingConnection(parameters)
        except pika.exceptions.AMQPConnectionError:
            print(f"RabbitMQ nije spreman ({retries})")
            retries -= 1
            time.sleep(3)
    raise Exception("RabbitMQ nedostupan")

def publish_to_rabbitmq(message):
    connection = None
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()

        channel.exchange_declare(
            exchange='table_events',
            exchange_type='fanout',
            durable=True
        )

        channel.basic_publish(
            exchange='table_events',
            routing_key='',
            body=json.dumps(message)
        )
    finally:
        if connection:
            connection.close()

def listen_to_rabbitmq():
    time.sleep(5)
    connection = get_rabbitmq_connection()
    channel = connection.channel()

    channel.exchange_declare(
        exchange='table_events',
        exchange_type='fanout',
        durable=True
    )

    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange='table_events', queue=queue_name)

    def callback(ch, method, properties, body):
        data = json.loads(body)
        socketio.emit('table_updated', data)

    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
    channel.start_consuming()

threading.Thread(target=listen_to_rabbitmq, daemon=True).start()

# =========================
# WEBSOCKET
# =========================

@socketio.on('connect')
def connect():
    print("Client connected")

@socketio.on('disconnect')
def disconnect():
    print("Client disconnected")

# =========================
# REST API
# =========================

@app.route('/api/clubs', methods=['GET'])
def get_clubs():
    return jsonify({"clubs": list(clubs_col.find({}, {"_id": 0}))})

@app.route('/api/clubs', methods=['POST'])
def add_club():
    data = request.get_json()
    clubs_col.insert_one(data)
    data.pop("_id", None)
    return jsonify({"success": True, "club": data}), 201

@app.route('/api/clubs/<club_id>/events')
def get_events(club_id):
    return jsonify({"events": list(events_col.find({"club_id": club_id}, {"_id": 0}))})

@app.route('/api/events/<event_id>/tables')
def get_tables(event_id):
    cache_key = f"tables_list_{event_id}"
    cached = cache.get(cache_key)

    if cached:
        return jsonify({"tables": json.loads(cached)})

    tables = list(tables_col.find({"event_id": event_id}))
    for t in tables:
        t["_id"] = str(t["_id"])

    cache.setex(cache_key, 3600, json.dumps(tables))
    return jsonify({"tables": tables})

@app.route('/api/events/<event_id>/tables/<table_id>/reserve', methods=['POST'])
def reserve_table(event_id, table_id):
    user = session.get("username")

    result = tables_col.update_one(
        {"event_id": event_id, "id": table_id, "status": "free"},
        {"$set": {"status": "reserved", "reserved_by": user}}
    )

    if result.modified_count == 0:
        return jsonify({"success": False}), 409

    publish_to_rabbitmq({
        "type": "RESERVED",
        "event_id": event_id,
        "table_id": table_id
    })

    cache.delete(f"tables_list_{event_id}")
    return jsonify({"success": True})

@app.route('/api/events/<event_id>/tables/<table_id>/cancel', methods=['POST'])
def cancel_table(event_id, table_id):
    tables_col.update_one(
        {"event_id": event_id, "id": table_id},
        {"$set": {"status": "free"}}
    )

    publish_to_rabbitmq({
        "type": "CANCELED",
        "event_id": event_id,
        "table_id": table_id
    })

    cache.delete(f"tables_list_{event_id}")
    return jsonify({"success": True})

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    if not users_col.find_one({"username": data["username"]}):
        users_col.insert_one(data)
    return jsonify({"success": True})

# =========================
# ENTRYPOINT
# =========================

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
