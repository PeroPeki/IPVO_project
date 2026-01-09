from flask import Flask, jsonify, request
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId

app = Flask(__name__)

# Mongo connection
client = MongoClient("mongodb://mongo:27017")
db = client["mydb"]

clubs_col = db["clubs"]
events_col = db["events"]
tables_col = db["tables"]
reservations_col = db["reservations"]
users_col = db["users"]
tickets_col = db["tickets"]

# ========== HELPER FUNKCIJE ==========

def serialize_doc(doc):
    """Konvertiraj MongoDB document u JSON"""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize_doc(d) for d in doc]
    if isinstance(doc, dict):
        doc.pop('_id', None)  # Uklanja _id (ObjectId)
        return doc
    return doc

# ========== CLUBS ENDPOINTS ==========

@app.get("/api/clubs")
def get_clubs():
    clubs = list(clubs_col.find({}, {"_id": 0}))
    return jsonify({"clubs": clubs})


@app.post("/api/clubs")
def add_club():
    data = request.get_json()
    required = ["id", "name", "location", "description"]
    if not data or any(k not in data for k in required):
        return jsonify({"success": False, "message": "Nedostaju polja"}), 400

    if not data["id"].strip():
        return jsonify({"success": False, "message": "ID je obavezan"}), 400

    club = {
        "id": data["id"],
        "name": data["name"],
        "location": data["location"],
        "description": data["description"],
    }

    clubs_col.insert_one(club)
    return jsonify({"success": True, "club": club}), 201


@app.delete("/api/clubs/<club_id>")
def delete_club(club_id):
    result = clubs_col.delete_one({"id": club_id})

    if result.deleted_count == 0:
        return jsonify({"success": False, "message": "Klub ne postoji"}), 404

    events_col.delete_many({"club_id": club_id})
    tables_col.delete_many({"club_id": club_id})
    reservations_col.delete_many({"club_id": club_id})

    return jsonify({"success": True}), 200

# ========== EVENTS ENDPOINTS ==========

@app.get("/api/clubs/<club_id>/events")
def get_events_for_club(club_id):
    events = list(events_col.find({"club_id": club_id}, {"_id": 0}))
    return jsonify({"events": events})

# ========== TABLES ENDPOINTS ==========

@app.get("/api/events/<event_id>/tables")
def get_tables_for_event(event_id):
    tables = list(tables_col.find({"event_id": event_id}, {"_id": 0}))
    return jsonify({"tables": tables})


@app.post("/api/events/<event_id>/tables/<table_id>/reserve")
def reserve_table(event_id, table_id):
    table = tables_col.find_one({"event_id": event_id, "id": table_id}, {"_id": 0})
    if not table:
        return jsonify({"success": False, "message": "Stol ne postoji"}), 404

    if table.get("status") == "reserved":
        return jsonify({"success": False, "message": "Stol je već zauzet"}), 409

    tables_col.update_one(
        {"event_id": event_id, "id": table_id},
        {"$set": {"status": "reserved"}}
    )

    reservations_col.insert_one({
        "event_id": event_id,
        "table_id": table_id,
        "status": "booked",
        "created_at": datetime.utcnow().isoformat() + "Z"
    })

    table["status"] = "reserved"
    return jsonify({"success": True, "table": table}), 201


@app.post("/api/events/<event_id>/tables/<table_id>/cancel")
def cancel_table(event_id, table_id):
    table = tables_col.find_one({"event_id": event_id, "id": table_id}, {"_id": 0})
    if not table:
        return jsonify({"success": False, "message": "Stol ne postoji"}), 404

    if table.get("status") == "free":
        return jsonify({"success": False, "message": "Stol je već slobodan"}), 409

    tables_col.update_one(
        {"event_id": event_id, "id": table_id},
        {"$set": {"status": "free"}}
    )

    reservations_col.update_one(
        {"event_id": event_id, "table_id": table_id, "status": "booked"},
        {"$set": {"status": "canceled"}}
    )

    table["status"] = "free"
    return jsonify({"success": True, "table": table}), 200

# ========== USERS ENDPOINTS ==========

@app.post("/api/users")
def create_user():
    data = request.get_json()
    username = data.get("username", "").strip()
    
    if not username:
        return jsonify({"success": False, "message": "Username je obavezan"}), 400
    
    # Provjeri da li korisnik već postoji
    existing = users_col.find_one({"username": username})
    if existing:
        return jsonify({"success": True, "message": "Korisnik već postoji"}), 200
    
    # Kreiraj novog korisnika
    user = {
        "username": username,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    
    users_col.insert_one(user)
    user.pop('_id', None)  # Uklanja ObjectId prije returnanja
    return jsonify({"success": True, "user": user}), 201

# ========== TICKET ENDPOINTS ==========

@app.post("/api/users/<username>/buy-ticket/<event_id>")
def buy_ticket(username, event_id):
    print(f"DEBUG: buy_ticket({username}, {event_id})")
    
    try:
        # Provjeri da li korisnik postoji
        user = users_col.find_one({"username": username})
        if not user:
            print(f"DEBUG: Korisnik {username} ne postoji")
            return jsonify({"success": False, "message": "Korisnik ne postoji"}), 404
        
        # Provjeri da li event postoji
        event = events_col.find_one({"id": event_id})
        if not event:
            print(f"DEBUG: Event {event_id} ne postoji")
            return jsonify({"success": False, "message": "Event ne postoji"}), 404
        
        # Provjeri da li već ima kartu za ovaj event
        existing_ticket = tickets_col.find_one({
            "username": username,
            "event_id": event_id
        })
        if existing_ticket:
            print(f"DEBUG: {username} već ima kartu za {event_id}")
            return jsonify({"success": False, "message": "Već ste kupili kartu za ovaj event"}), 409
        
        # Kreiraj novu kartu
        ticket = {
            "id": f"ticket-{username}-{event_id}",
            "username": username,
            "event_id": event_id,
            "bought_at": datetime.utcnow().isoformat() + "Z"
        }
        
        print(f"DEBUG: Kreiram kartu: {ticket}")
        tickets_col.insert_one(ticket)
        
        # Uklanja _id prije slanja
        ticket.pop('_id', None)
        
        print(f"DEBUG: Karta uspješno kupljena")
        return jsonify({"success": True, "ticket": ticket}), 201
    
    except Exception as e:
        print(f"ERROR u buy_ticket: {str(e)}")
        return jsonify({"success": False, "message": f"Greška: {str(e)}"}), 500


@app.get("/api/users/<username>/has-ticket/<event_id>")
def has_ticket(username, event_id):
    print(f"DEBUG: has_ticket({username}, {event_id})")
    
    try:
        ticket = tickets_col.find_one({
            "username": username,
            "event_id": event_id
        }, {"_id": 0})
        
        has_it = ticket is not None
        print(f"DEBUG: has_ticket result = {has_it}")
        return jsonify({"hasTicket": has_it}), 200
    
    except Exception as e:
        print(f"ERROR u has_ticket: {str(e)}")
        return jsonify({"hasTicket": False}), 200


@app.get("/api/users/<username>/tickets")
def get_user_tickets(username):
    tickets = list(tickets_col.find({"username": username}, {"_id": 0}))
    return jsonify({"tickets": tickets}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
