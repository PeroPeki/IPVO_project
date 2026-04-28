from gevent import monkey
monkey.patch_all()

from flask import Flask, jsonify, request, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
import pika
import json
import threading
import time
import redis
from flask import g
from flask import Response


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
                
                # OVDJE se događa 'Real-Time' magija:
                # Šaljemo podatak svim spojenim klijentima
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

# ==========================================
# WEBSOCKET HANDLERI
# ==========================================

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")

# ==========================================
# REST API RUTE
# ==========================================

@app.route('/api/clubs', methods=['GET'])
def get_clubs():
    clubs = list(clubs_col.find({}, {"_id": 0}))
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
    events = list(events_col.find({"club_id": club_id}, {"_id": 0}))
    return jsonify({"events": events})



# ==========================================
# REDIS
# ==========================================



import json
from flask import jsonify, request, session
from datetime import datetime

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
    
    user_name = session.get('username')
    
    # Update samo ako je stol 'free'
    result = tables_col.update_one(
        {"event_id": event_id, "id": table_id, "status": "free"},
        {"$set": {"status": "reserved", "reserved_by": user_name}}
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
    """Otkazivanje rezervacije - s invalidacijom cachea"""
    
    table = tables_col.find_one({"event_id": event_id, "id": table_id})
    
    if not table:
        return jsonify({"success": False, "message": "Stol ne postoji"}), 404
    
    if table.get("status") == "free":
        return jsonify({"success": False, "message": "Stol je već slobodan"}), 409
    
    # Update u bazi
    tables_col.update_one(
        {"event_id": event_id, "id": table_id},
        {"$set": {"status": "free"}}
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


def request_price_update(event_id, event_data):
    """Šalje zahtjev za ažuriranjem cijene asinkrono putem RabbitMQ-a."""
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        channel.queue_declare(queue="price_update_queue", durable=True)

        message = {
            "event_id": str(event_id),
            "artist_listeners": event_data.get("artist_listeners", 0),
            "artist_playcount": event_data.get("artist_playcount", 0),
            "genre_encoded": event_data.get("genre_encoded", 0),
            "venue_capacity": event_data.get("venue_capacity", 500),
            "days_until_event": event_data.get("days_until_event", 30),
            "tickets_sold_ratio": calculate_tickets_sold_ratio(event_id),
            "day_of_week": datetime.utcnow().weekday(),
            "current_price": event_data.get("current_price", 60.0),
        }

        channel.basic_publish(
            exchange="",
            routing_key="price_update_queue",
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        connection.close()
    except Exception as e:
        print(f"Greška pri slanju price update zahtjeva: {e}")


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
    import requests as req
    try:
        response = req.get("http://prediction_service:6000/model-info", timeout=5)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 503


@app.route('/api/events/<event_id>/pricing', methods=['GET'])
def get_event_pricing(event_id):
    """Vraća pricing podatke (base/current/min/max) za pojedini event."""
    event = events_col.find_one({"id": event_id}) or events_col.find_one(
        {"ticketmaster_id": event_id}
    )
    if not event:
        return jsonify({"error": "Event ne postoji"}), 404

    return jsonify({
        "event_id": event_id,
        "base_price": event.get("base_price"),
        "current_price": event.get("current_price"),
        "min_price": event.get("min_price"),
        "max_price": event.get("max_price"),
        "artist_name": event.get("artist_name"),
        "venue_capacity": event.get("venue_capacity"),
    })


@app.route('/api/events/<event_id>/request-price-update', methods=['POST'])
def trigger_price_update(event_id):
    """Ručno okidanje price update zahtjeva za pojedini event."""
    event = events_col.find_one({"id": event_id}) or events_col.find_one(
        {"ticketmaster_id": event_id}
    )
    if not event:
        return jsonify({"success": False, "message": "Event ne postoji"}), 404

    request_price_update(event.get("id") or event.get("ticketmaster_id"), event)
    return jsonify({"success": True, "message": "Price update zahtjev poslan"}), 202





# ==========================================
# MAIN ENTRY POINT
# ==========================================

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)