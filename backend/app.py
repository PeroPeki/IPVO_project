from gevent import monkey
monkey.patch_all()

from flask import Flask, jsonify, request, session, g, Response
from flask_socketio import SocketIO, emit, join_room, leave_room
from pymongo import MongoClient
from datetime import datetime, timezone
from bson import ObjectId
import pika
import json
import threading
import time
import redis
import requests as ext_requests


from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

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

# Inicijalizacija SocketIO s podrškom za CORS
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

# Mongo Connection
# Spajamo se na 'mongo' servis definiran u docker-compose
client = MongoClient("mongodb://mongo:27017", connect = False)
db = client["mydb"]

# Kolekcije
clubs_col = db["clubs"]
events_col = db["events"]
tables_col = db["tables"]
reservations_col = db["reservations"]
users_col = db["users"]
tickets_col = db["tickets"]
price_log_col = db["price_log"]
ml_training_col = db["ml_training_data"]
model_metadata_col = db["model_metadata"]

# ==========================================
# MONGODB INDEKSI
# ==========================================

def ensure_indexes():
    """
    Kreira sve potrebne MongoDB indekse pri startu aplikacije.
    Idempotentno – pymongo preskače indeks ako već postoji s istim imenom i opcijama.
    Zamjenjuje bivši seed-tools/seed.js kontejner.
    """
    try:
        clubs_col.create_index([("id", 1)], unique=True)
        events_col.create_index([("ticketmaster_id", 1)], unique=True, sparse=True)
        events_col.create_index([("id", 1)])
        events_col.create_index([("club_id", 1)])
        events_col.create_index([("city", 1), ("country", 1)])
        events_col.create_index([("event_date", 1)])
        tables_col.create_index([("event_id", 1)])
        tables_col.create_index([("id", 1)])
        reservations_col.create_index([("event_id", 1), ("table_id", 1)])
        print("[indexes] MongoDB indeksi su osigurani.")
    except Exception as exc:
        print(f"[indexes] Greška pri kreiranju indeksa: {exc}")

ensure_indexes()

# ==========================================
# RABBITMQ FUNKCIONALNOST (Producer & Consumer)
# ==========================================

def get_rabbitmq_connection():
    """Pomoćna funkcija za spajanje na RabbitMQ s retry logikom."""
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
            print(f"RabbitMQ nije spreman, čekam... ({retries} preostalo)")
            retries -= 1
            time.sleep(3)
    raise Exception("Ne mogu se spojiti na RabbitMQ")

def publish_to_rabbitmq(message):
    """
    PRODUCER: Šalje poruku u RabbitMQ exchange 'table_events'.
    Poziva se iz API ruta (reserve/cancel).
    """
    connection = None
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        
        # Fanout exchange šalje poruku svim queuevima koji su bindani na njega
        channel.exchange_declare(
            exchange='table_events',
            exchange_type='fanout',
            durable=True
        )
        
        body = json.dumps(message)
        channel.basic_publish(
            exchange='table_events',
            routing_key='',
            body=body
        )
        
        print(f" [x] Poslano u RabbitMQ: {message}")
        
    except Exception as e:
        print(f" [!] Greška pri slanju u RabbitMQ: {e}")
    finally:
        if connection:
            connection.close()

def listen_to_rabbitmq():
    """
    CONSUMER: Pozadinska dretva koja sluša RabbitMQ.
    Kada primi poruku, prosljeđuje je klijentima preko Socket.IO.
    """
    # Malo pričekamo da se RabbitMQ servis sigurno podigne pri startu kontejnera
    time.sleep(5)
    
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        
        channel.exchange_declare(
            exchange='table_events',
            exchange_type='fanout',
            durable=True
        )
        
        # Kreiramo privremeni, ekskluzivni queue za ovu instancu backenda
        result = channel.queue_declare(queue='', exclusive=True)
        queue_name = result.method.queue
        
        channel.queue_bind(exchange='table_events', queue=queue_name)
        
        print(f"Backend Consumer sluša na redu: {queue_name}")

        def callback(ch, method, properties, body):
            try:
                data = json.loads(body)
                print(f"RabbitMQ -> SocketIO: {data}")

                # Emitiramo samo klijentima u sobi za taj event (ako ima event_id)
                event_id = data.get('event_id')
                if event_id:
                    socketio.emit('table_updated', data, room=f"event_{event_id}")
                else:
                    socketio.emit('table_updated', data)

            except Exception as e:
                print(f"Greška u consumer callbacku: {e}")

        channel.basic_consume(
            queue=queue_name,
            on_message_callback=callback,
            auto_ack=True
        )
        
        channel.start_consuming()
        
    except Exception as e:
        print(f"RabbitMQ Consumer Thread umro: {e}")

# Pokreni RabbitMQ Consumera u pozadini
# Daemon=True znači da će se ugasiti kad se ugasi glavna aplikacija
rabbitmq_thread = threading.Thread(target=listen_to_rabbitmq, daemon=True)
rabbitmq_thread.start()


def kickoff_initial_pipeline():
    """Na startup-u, ako je baza prazna, okida Ticketmaster pipeline preko Celeryja."""
    time.sleep(8)  # daj RabbitMQ-u i Mongu da se podignu
    try:
        existing = events_col.count_documents({"source": "ticketmaster"})
        if existing > 0:
            print(f"[bootstrap] Events kolekcija sadrži {existing} TM eventa – preskačem.")
            return
        print("[bootstrap] Events prazna – pokrećem run_data_pipeline preko Celeryja...")
        from celery import Celery
        celery_app = Celery("tasks", broker="amqp://guest:guest@rabbitmq:5672//")
        celery_app.send_task("tasks.run_data_pipeline")
        print("[bootstrap] run_data_pipeline poslan u Celery queue.")
    except Exception as exc:
        print(f"[bootstrap] Greška pri pokretanju pipelinea: {exc}")


bootstrap_thread = threading.Thread(target=kickoff_initial_pipeline, daemon=True)
bootstrap_thread.start()

# ==========================================
# WEBSOCKET HANDLERI
# ==========================================

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")

@socketio.on('join_event')
def handle_join_event(data):
    event_id = data.get('event_id')
    if event_id:
        join_room(f"event_{event_id}")
        print(f"Klijent {request.sid} pridružio se sobi event_{event_id}")

@socketio.on('leave_event')
def handle_leave_event(data):
    event_id = data.get('event_id')
    if event_id:
        leave_room(f"event_{event_id}")
        print(f"Klijent {request.sid} napustio sobu event_{event_id}")

# ==========================================
# REST API RUTE
# ==========================================

@app.route('/api/clubs', methods=['GET'])
def get_clubs():
    """Lista klubova/venuea s opcionalnim filterima ?city=, ?country=."""
    city = request.args.get("city")
    country = request.args.get("country")

    query = {}
    if city:
        query["city"] = {"$regex": f"^{city}$", "$options": "i"}
    if country:
        query["country"] = country.upper()

    # Jedan aggregation upit dohvaća klubove + event_count (bez N+1)
    pipeline = [
        {"$match": query},
        {"$lookup": {
            "from": "events",
            "localField": "id",
            "foreignField": "club_id",
            "as": "_events",
        }},
        {"$addFields": {"event_count": {"$size": "$_events"}}},
        {"$project": {"_id": 0, "_events": 0}},
        {"$sort": {"name": 1}},
    ]
    clubs = list(clubs_col.aggregate(pipeline))
    return jsonify({"clubs": clubs})

@app.route('/api/clubs', methods=['POST'])
def add_club():
    data = request.get_json()
    # Jednostavna validacija
    if not data or "id" not in data:
        return jsonify({"success": False, "message": "Fali ID"}), 400

    clubs_col.insert_one(data)
    # Uklanjamo _id za response
    if "_id" in data: del data["_id"]
    return jsonify({"success": True, "club": data}), 201

@app.route('/api/clubs/<club_id>/events', methods=['GET'])
def get_events(club_id):
    events = list(
        events_col.find({"club_id": club_id}, {"_id": 0})
        .sort("event_date", 1)
    )
    return jsonify({"events": events})


@app.route('/api/events', methods=['GET'])
def get_all_events():
    """Globalni feed eventa s filtriranjem (?city=, ?country=, ?genre=, ?q=, ?limit=)."""
    city = request.args.get("city")
    country = request.args.get("country")
    genre = request.args.get("genre")
    query_text = request.args.get("q")
    try:
        limit = min(int(request.args.get("limit", 100)), 500)
    except ValueError:
        limit = 100

    query = {"source": "ticketmaster"}
    if city:
        query["city"] = {"$regex": f"^{city}$", "$options": "i"}
    if country:
        query["country"] = country.upper()
    if genre:
        query["$or"] = [
            {"genre_name": {"$regex": genre, "$options": "i"}},
            {"tm_genre": {"$regex": genre, "$options": "i"}},
        ]
    if query_text:
        query["$or"] = (query.get("$or", [])) + [
            {"name": {"$regex": query_text, "$options": "i"}},
            {"artist_name": {"$regex": query_text, "$options": "i"}},
            {"venue_name": {"$regex": query_text, "$options": "i"}},
        ]

    cache_key = f"events_global_{city}_{country}_{genre}_{query_text}_{limit}"
    cached = cache.get(cache_key)
    if cached:
        return jsonify(json.loads(cached))

    events = list(
        events_col.find(query, {"_id": 0})
        .sort("event_date", 1)
        .limit(limit)
    )
    payload = {"events": events, "count": len(events)}
    cache.setex(cache_key, 60, json.dumps(payload, default=str))
    return jsonify(payload)


@app.route('/api/events/<event_id>', methods=['GET'])
def get_event_detail(event_id):
    """Detalji jednog eventa (po internom id ili ticketmaster_id)."""
    event = events_col.find_one(
        {"$or": [{"id": event_id}, {"ticketmaster_id": event_id}]},
        {"_id": 0},
    )
    if not event:
        return jsonify({"error": "Event ne postoji"}), 404
    return jsonify(event)


@app.route('/api/cities', methods=['GET'])
def get_cities():
    """Agregira gradove + broj eventa po gradu (za filter dropdowne)."""
    pipeline = [
        {"$match": {"source": "ticketmaster"}},
        {"$group": {
            "_id": {"city": "$city", "country": "$country"},
            "event_count": {"$sum": 1},
        }},
        {"$sort": {"event_count": -1}},
    ]
    cities = []
    for doc in events_col.aggregate(pipeline):
        cities.append({
            "city": doc["_id"].get("city"),
            "country": doc["_id"].get("country"),
            "event_count": doc["event_count"],
        })
    return jsonify({"cities": cities})


@app.route('/api/sync-events', methods=['POST'])
def trigger_sync():
    """Ručno okida data pipeline (TM dohvat + Last.fm obogaćivanje)."""
    try:
        from celery import Celery
        celery_app = Celery("tasks", broker="amqp://guest:guest@rabbitmq:5672//")
        task = celery_app.send_task("tasks.run_data_pipeline")
        return jsonify({
            "success": True,
            "message": "Pipeline pokrenut u pozadini",
            "task_id": str(task.id),
        }), 202
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500



# ==========================================
# REDIS
# ==========================================

@app.route('/api/events/<event_id>/tables', methods=['GET'])
def get_tables(event_id):
    """Dohvaćanje stolova s cachingom u Redis"""
    
    cache_key = f'tables_list_{event_id}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        print(f"Dohvaćam stolove iz Redisa! (event: {event_id})")
        # Vrati JSON iz cachea
        return jsonify({"tables": json.loads(cached_data)})
    
    print(f"Dohvaćam stolove iz MongoDB... (event: {event_id})")
    
    tables = list(tables_col.find({"event_id": event_id}))
    
    # Kovertiraj ObjectId u stringove za JSON serializaciju
    for table in tables:
        table['_id'] = str(table['_id'])
    
    # Spremanje liste stolova u Redis cache na 1 sat (3600 sekundi)
    cache.setex(cache_key, 3600, json.dumps(tables))
    
    return jsonify({"tables": tables})


@app.route('/api/events/<event_id>/tables/<table_id>/reserve', methods=['POST'])
def reserve_table(event_id, table_id):
    """Rezervacija stola - s invalidacijom Redis cachea"""

    data = request.get_json(silent=True) or {}
    user_name = (
        data.get('username')
        or request.args.get('username')
        or session.get('username')
    )

    # Update samo ako je stol 'free'
    result = tables_col.update_one(
        {"event_id": event_id, "id": table_id, "status": "free"},
        {"$set": {
            "status": "reserved",
            "reserved_by": user_name,
            "reserved_at": datetime.utcnow(),
        }}
    )

    if result.modified_count > 0:
        # Zabilježi u kolekciju
        reservations_col.insert_one({
            "event_id": event_id,
            "table_id": table_id,
            "user": user_name,
            "status": "booked",
            "timestamp": datetime.utcnow().isoformat()
        })

        # Pošalji event kroz RabbitMQ
        publish_to_rabbitmq({
            "type": "RESERVED",
            "event_id": event_id,
            "table_id": table_id,
            "status": "reserved"
        })

        # Brisanje cachea da bi se osvježio pri idućem dohvaćanju
        cache_key = f'tables_list_{event_id}'
        cache.delete(cache_key)
        print(f"Cache obrisan (rezervacija) za event: {event_id}")

        return jsonify({"success": True, "message": "Stol je rezerviran"}), 200

    return jsonify({"success": False, "message": "Stol nije dostupan"}), 409


@app.route('/api/events/<event_id>/tables/<table_id>/cancel', methods=['POST'])
def cancel_table(event_id, table_id):
    """Otkazivanje rezervacije - s invalidacijom cachea i provjerom vlasništva"""

    data = request.get_json(silent=True) or {}
    user_name = (
        data.get('username')
        or request.args.get('username')
        or session.get('username')
    )

    table = tables_col.find_one({"event_id": event_id, "id": table_id})

    if not table:
        return jsonify({"success": False, "message": "Stol ne postoji"}), 404

    if table.get("status") == "free":
        return jsonify({"success": False, "message": "Stol je već slobodan"}), 409

    # Provjera vlasništva — samo korisnik koji je rezervirao može otkazati
    reserved_by = table.get("reserved_by")
    if reserved_by and reserved_by != user_name:
        return jsonify({
            "success": False,
            "message": "Nemate pravo otkazati ovu rezervaciju",
        }), 403

    # Update u bazi
    tables_col.update_one(
        {"event_id": event_id, "id": table_id},
        {"$set": {"status": "free"}, "$unset": {"reserved_by": "", "reserved_at": ""}}
    )

    # Pošalji event
    publish_to_rabbitmq({
        "type": "CANCELED",
        "event_id": event_id,
        "table_id": table_id,
        "status": "free"
    })

    # Obriši cache
    cache_key = f'tables_list_{event_id}'
    cache.delete(cache_key)
    print(f"Cache obrisan (otkazivanje) za event: {event_id}")

    return jsonify({"success": True, "message": "Rezervacija je otkazana"}), 200



# Korisnici i ulaznice (User management)
@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    username = data.get("username")
    if not users_col.find_one({"username": username}):
        users_col.insert_one({"username": username})
    return jsonify({"success": True, "user": {"username": username}}), 201

@app.route('/api/users/<username>/buy-ticket/<event_id>', methods=['POST'])
def buy_ticket(username, event_id):
    if tickets_col.find_one({"username": username, "event_id": event_id}):
        return jsonify({"success": False, "message": "Već imate kartu"}), 409
        
    tickets_col.insert_one({
        "username": username,
        "event_id": event_id,
        "bought_at": datetime.utcnow().isoformat()
    })
    return jsonify({"success": True}), 201

@app.route('/api/users/<username>/has-ticket/<event_id>', methods=['GET'])
def has_ticket(username, event_id):
    ticket = tickets_col.find_one({"username": username, "event_id": event_id})
    return jsonify({"hasTicket": ticket is not None}), 200

@app.route('/api/reports', methods=['GET'])
def get_reports():
    # Dohvati zadnjih 10 izvještaja
    reports = list(db.reports.find({}, {"_id": 0}).sort("date", -1).limit(10))
    return jsonify({"reports": reports})


# ==========================================
# FAZA 4 – DYNAMIC PRICING INTEGRACIJA
# ==========================================

def calculate_tickets_sold_ratio(event_id):
    """Izračunava udio rezerviranih stolova iz internih podataka."""
    try:
        total = tables_col.count_documents({"event_id": event_id})
        reserved = tables_col.count_documents(
            {"event_id": event_id, "status": "reserved"}
        )
        return round(reserved / total, 2) if total > 0 else 0.0
    except Exception:
        return 0.5


_rabbitmq_lock = threading.Lock()
_rabbitmq_pool_connection = None
_rabbitmq_pool_channel = None


def get_rabbitmq_channel():
    """Globalni RabbitMQ channel s lazy inicijalizacijom i auto-reconnectom."""
    global _rabbitmq_pool_connection, _rabbitmq_pool_channel
    with _rabbitmq_lock:
        try:
            if _rabbitmq_pool_connection is None or _rabbitmq_pool_connection.is_closed:
                _rabbitmq_pool_connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host="rabbitmq",
                        heartbeat=600,
                        blocked_connection_timeout=300,
                    )
                )
                _rabbitmq_pool_channel = _rabbitmq_pool_connection.channel()
                _rabbitmq_pool_channel.queue_declare(queue="price_update_queue", durable=True)
        except Exception as e:
            print(f"RabbitMQ konekcija greška: {e}")
            _rabbitmq_pool_connection = None
            _rabbitmq_pool_channel = None
            raise
        return _rabbitmq_pool_channel


def request_price_update(event_id, event_data):
    """Šalje zahtjev za ažuriranjem cijene asinkrono putem RabbitMQ-a."""
    global _rabbitmq_pool_connection

    # Izračunaj days_until_event dinamički iz event_date
    days_until = 30
    event_date_raw = event_data.get("event_date")
    if event_date_raw:
        try:
            if isinstance(event_date_raw, str):
                event_date = datetime.fromisoformat(event_date_raw.replace("Z", "+00:00"))
            else:
                event_date = event_date_raw
            now = datetime.now(timezone.utc) if event_date.tzinfo else datetime.utcnow()
            days_until = max(0, (event_date - now).days)
        except Exception:
            pass

    message = {
        "event_id": str(event_id),
        "artist_listeners": event_data.get("artist_listeners", 0),
        "artist_playcount": event_data.get("artist_playcount", 0),
        "genre_encoded": event_data.get("genre_encoded", 0),
        "venue_capacity": event_data.get("venue_capacity", 500),
        "days_until_event": days_until,
        "tickets_sold_ratio": calculate_tickets_sold_ratio(event_id),
        "day_of_week": datetime.utcnow().weekday(),
        "current_price": event_data.get("current_price", 60.0),
    }

    try:
        channel = get_rabbitmq_channel()
        channel.basic_publish(
            exchange="",
            routing_key="price_update_queue",
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2),
        )
    except Exception as e:
        print(f"Greška pri slanju price update zahtjeva: {e}")
        with _rabbitmq_lock:
            _rabbitmq_pool_connection = None


@app.route('/api/price-log', methods=['GET'])
def get_price_log():
    """Vraća zadnjih 50 zapisa promjene cijena."""
    logs = list(
        price_log_col.find({}, {"_id": 0}).sort("timestamp", -1).limit(50)
    )
    for log in logs:
        if isinstance(log.get("timestamp"), datetime):
            log["timestamp"] = log["timestamp"].isoformat()
    return jsonify({"price_log": logs})


@app.route('/api/model-status', methods=['GET'])
def get_model_status():
    """Proxy prema /model-info endpointu Prediction Servicea."""
    try:
        response = ext_requests.get("http://prediction_service:6000/model-info", timeout=5)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 503


@app.route('/api/events/<event_id>/pricing', methods=['GET'])
def get_event_pricing(event_id):
    """Vraća pricing podatke (base/current/min/max + high_demand) za event.

    Prvo gleda u Redis cache, pa onda u MongoDB.
    """
    cache_key = f"event_pricing_{event_id}"
    cached = cache.get(cache_key)
    if cached:
        return jsonify(json.loads(cached))

    event = events_col.find_one(
        {"$or": [{"id": event_id}, {"ticketmaster_id": event_id}]}
    )
    if not event:
        return jsonify({"error": "Event ne postoji"}), 404

    base_price = event.get("base_price") or 0.0
    current_price = event.get("current_price") or base_price
    high_demand = bool(base_price and current_price > base_price * 1.2)

    payload = {
        "event_id": event_id,
        "base_price": base_price,
        "current_price": current_price,
        "min_price": event.get("min_price"),
        "max_price": event.get("max_price"),
        "high_demand": high_demand,
        "artist_name": event.get("artist_name"),
        "venue_capacity": event.get("venue_capacity"),
    }

    cache.setex(cache_key, 60, json.dumps(payload))
    return jsonify(payload)


@app.route('/api/events/<event_id>/request-price-update', methods=['POST'])
def trigger_price_update(event_id):
    """Ručno okidanje price update zahtjeva za pojedini event."""
    event = events_col.find_one(
        {"$or": [{"id": event_id}, {"ticketmaster_id": event_id}]}
    )
    if not event:
        return jsonify({"success": False, "message": "Event ne postoji"}), 404

    request_price_update(event.get("id") or event.get("ticketmaster_id"), event)
    return jsonify({"success": True, "message": "Price update zahtjev poslan"}), 202


def notify_price_update(event_id, new_price, base_price):
    """Obavještava sve klijente na eventu o promjeni cijene preko SocketIO sobe."""
    try:
        high_demand = bool(base_price and new_price > base_price * 1.2)
        socketio.emit('price_updated', {
            "event_id": str(event_id),
            "current_price": new_price,
            "high_demand": high_demand,
        }, room=f"event_{event_id}")
    except Exception as exc:
        print(f"Greška pri emit-u price_updated: {exc}")


@app.route('/api/events/<event_id>/notify-price-change', methods=['POST'])
def notify_price_change(event_id):
    """Interni endpoint koji prediction service poziva nakon što ažurira cijenu.

    Emitira `price_updated` socket event svim klijentima koji slušaju ovaj event.
    """
    data = request.get_json(silent=True) or {}
    new_price = data.get('new_price')
    base_price = data.get('base_price')
    if new_price is None:
        event = events_col.find_one(
            {"$or": [{"id": event_id}, {"ticketmaster_id": event_id}]}
        )
        if not event:
            return jsonify({"success": False, "message": "Event ne postoji"}), 404
        new_price = event.get('current_price') or 0
        base_price = base_price if base_price is not None else event.get('base_price') or 0

    notify_price_update(event_id, float(new_price), float(base_price or 0))
    return jsonify({"success": True}), 200





# ==========================================
# MAIN ENTRY POINT
# ==========================================

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)