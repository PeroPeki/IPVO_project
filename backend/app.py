from gevent import monkey
monkey.patch_all()

"""
NightClub Manager v2 — Flask backend.

- REST API pod /api/* (blueprintovi u routes/)
- JWT autentikacija (user / admin / superadmin / hostess / waiter) + revokacija
- Socket.IO real-time kanal kroz Redis message queue (realtime.py)
- Rate limiting na auth rutama (flask-limiter, Redis storage)
- Stripe webhook za potvrde plaćanja
- Prometheus /metrics endpoint
"""

import os
import re
import time

import stripe
from bson.errors import InvalidId
from flask import Flask, Response, g, jsonify, request, send_from_directory, session
from flask_jwt_extended import JWTManager, decode_token
from flask_socketio import SocketIO, join_room, leave_room
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from werkzeug.middleware.proxy_fix import ProxyFix

from db import ensure_indexes
from extensions import limiter, redis_client
from payments import handle_payment_intent_succeeded
from realtime import SOCKETIO_MESSAGE_QUEUE
from routes import ALL_BLUEPRINTS
from upload_service import UPLOAD_DIR

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
if JWT_SECRET == "dev-secret-change-me":
    print(
        "[SECURITY] UPOZORENJE: JWT_SECRET nije postavljen — koristi se dev tajna. "
        "Za produkciju postavi JWT_SECRET u .env (openssl rand -hex 32)."
    )

app = Flask(__name__)
# Traefik postavlja X-Forwarded-* — bez ovoga rate limiter vidi samo IP proxyja
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config["SECRET_KEY"] = JWT_SECRET
app.config["JWT_SECRET_KEY"] = JWT_SECRET
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 60 * 60 * 12       # 12h
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = 60 * 60 * 24 * 30  # 30 dana
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024          # 10 MB upload limit

jwt = JWTManager(app)
limiter.init_app(app)


@jwt.token_in_blocklist_loader
def token_revoked(_jwt_header, jwt_payload):
    """Logout/rotacija dodaju jti na blocklist u Redisu (vidi routes/auth.py)."""
    try:
        return redis_client.exists(f"revoked_jwt:{jwt_payload['jti']}") == 1
    except Exception:
        # Redis nedostupan — ne obaraj autentikaciju zbog infrastrukture
        return False


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

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="gevent",
    message_queue=SOCKETIO_MESSAGE_QUEUE,
)

STAFF_SOCKET_ROLES = ("waiter", "hostess", "admin", "superadmin")


@socketio.on("connect")
def handle_connect(auth):
    """Konekcija zahtijeva važeći JWT: klijent šalje auth={token}."""
    token = (auth or {}).get("token")
    if not token:
        return False
    try:
        claims = decode_token(token)
    except Exception:
        return False
    session["role"] = claims.get("role", "user")
    session["subject_id"] = claims.get("sub")


@socketio.on("join_event")
def handle_join_event(data):
    """Korisnici na stranici eventa — primaju table_updated."""
    event_id = (data or {}).get("event_id")
    if event_id and session.get("subject_id"):
        join_room(f"event_{event_id}")


@socketio.on("leave_event")
def handle_leave_event(data):
    event_id = (data or {}).get("event_id")
    if event_id:
        leave_room(f"event_{event_id}")


@socketio.on("join_waiter")
def handle_join_waiter(data):
    """Konobarski prikaz — konobar smije samo u vlastitu sobu."""
    waiter_id = (data or {}).get("waiter_id")
    role = session.get("role")
    if not waiter_id or role not in ("waiter", "admin", "superadmin"):
        return
    if role == "waiter" and session.get("subject_id") != str(waiter_id):
        return
    join_room(f"waiter_{waiter_id}")


@socketio.on("join_bar")
def handle_join_bar(data):
    """Barski zaslon — samo osoblje i admini."""
    event_id = (data or {}).get("event_id")
    if event_id and session.get("role") in STAFF_SOCKET_ROLES:
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
    if not re.fullmatch(r"[A-Za-z0-9_-]+", folder):
        return jsonify({"error": "Ruta ne postoji"}), 404
    return send_from_directory(os.path.join(UPLOAD_DIR, folder), filename)


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "service": "nightclub-manager-backend"})


@app.errorhandler(InvalidId)
def invalid_object_id(_):
    return jsonify({"error": "Neispravan ID"}), 400


@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "Ruta ne postoji"}), 404


@app.errorhandler(429)
def rate_limited(_):
    return jsonify({"error": "Previše zahtjeva — pokušajte ponovno kasnije"}), 429


@app.errorhandler(500)
def server_error(exc):
    return jsonify({"error": "Interna greška servera"}), 500


# =========================
# STARTUP
# =========================

ensure_indexes()


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
