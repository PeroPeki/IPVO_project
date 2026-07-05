from gevent import monkey
monkey.patch_all()

"""
NightClub Manager v2 — Flask backend.

- REST API pod /api/* (blueprintovi u routes/)
- JWT autentikacija (user / admin / superadmin / hostess / waiter)
- Socket.IO real-time kanal, napajan Redis Pub/Sub-om (realtime.py)
- Stripe webhook za potvrde plaćanja
- Prometheus /metrics endpoint
"""

import os
import time

import stripe
from flask import Flask, Response, g, jsonify, request, send_from_directory
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO, join_room, leave_room
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)

import realtime
from db import ensure_indexes
from payments import handle_payment_intent_succeeded
from routes import ALL_BLUEPRINTS
from upload_service import UPLOAD_DIR

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("JWT_SECRET", "dev-secret-change-me")
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET", "dev-secret-change-me")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 60 * 60 * 12       # 12h
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = 60 * 60 * 24 * 30  # 30 dana
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024          # 10 MB upload limit

jwt = JWTManager(app)

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


@app.before_request
def start_timer():
    g.start_time = time.time()


@app.after_request
def record_metrics(response):
    # Preskoči metrics i websocket promet
    if request.path.startswith("/metrics") or request.path.startswith("/socket.io"):
        return response

    latency = time.time() - g.start_time
    # Koristimo rutu (url_rule) umjesto sirove putanje da ne eksplodira kardinalnost
    endpoint = request.url_rule.rule if request.url_rule else request.path

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
# SOCKET.IO
# =========================

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="gevent")


@socketio.on("connect")
def handle_connect():
    print(f"Client connected: {request.sid}")


@socketio.on("disconnect")
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")


@socketio.on("join_event")
def handle_join_event(data):
    """Korisnici na stranici eventa — primaju table_updated."""
    event_id = (data or {}).get("event_id")
    if event_id:
        join_room(f"event_{event_id}")


@socketio.on("leave_event")
def handle_leave_event(data):
    event_id = (data or {}).get("event_id")
    if event_id:
        leave_room(f"event_{event_id}")


@socketio.on("join_waiter")
def handle_join_waiter(data):
    """Konobarski prikaz — prima order_updated za svoje narudžbe."""
    waiter_id = (data or {}).get("waiter_id")
    if waiter_id:
        join_room(f"waiter_{waiter_id}")


@socketio.on("join_bar")
def handle_join_bar(data):
    """Barski zaslon — prima sve order_updated za event."""
    event_id = (data or {}).get("event_id")
    if event_id:
        join_room(f"bar_{event_id}")


# =========================
# BLUEPRINTOVI
# =========================

for bp in ALL_BLUEPRINTS:
    app.register_blueprint(bp)


# =========================
# STRIPE WEBHOOK
# =========================

@app.route('/api/webhooks/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.environ.get('STRIPE_WEBHOOK_SECRET')
        )
    except Exception:
        return jsonify({"error": "Invalid"}), 400

    if event['type'] == 'payment_intent.succeeded':
        pi = event['data']['object']
        handle_payment_intent_succeeded(pi)

    return jsonify({"status": "ok"}), 200


# =========================
# OSTALO
# =========================

@app.route("/api/uploads/<folder>/<filename>")
def serve_upload(folder, filename):
    """Servira lokalno spremljene slike (razvoj bez Cloudinaryja)."""
    return send_from_directory(os.path.join(UPLOAD_DIR, folder), filename)


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "service": "nightclub-manager-backend"})


@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "Ruta ne postoji"}), 404


@app.errorhandler(500)
def server_error(exc):
    return jsonify({"error": "Interna greška servera"}), 500


# =========================
# STARTUP
# =========================

ensure_indexes()
realtime.start_listener(socketio)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
