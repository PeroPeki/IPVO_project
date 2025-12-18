from flask import Flask, jsonify, request

app = Flask(__name__)

# privremeni "fake" podaci
CLUBS = [
    {"id": "c1", "name": "Club A", "location": "Centar grada", "description": "Najpoznatiji klub u gradu"},
    {"id": "c2", "name": "Club B", "location": "Primorski dio", "description": "Luksuzni klub uz more"},
]

EVENTS = [
    {"id": "e1", "club_id": "c1", "name": "Techno Night", "date": "20.12.2025", "description": "Najbolji DJ-evi od 22h"},
    {"id": "e2", "club_id": "c1", "name": "House Night", "date": "21.12.2025", "description": "House glazba cijelu noć"},
    {"id": "e3", "club_id": "c2", "name": "RNB Night", "date": "22.12.2025", "description": "RnB i hip-hop best hits"},
]

TABLES = {
    "e1": [
        {"id": "t1", "number": 1, "status": "free"},
        {"id": "t2", "number": 2, "status": "free"},
        {"id": "t3", "number": 3, "status": "reserved"},
        {"id": "t4", "number": 4, "status": "free"},
    ],
    "e2": [
        {"id": "t5", "number": 1, "status": "free"},
        {"id": "t6", "number": 2, "status": "free"},
    ],
    "e3": [
        {"id": "t7", "number": 1, "status": "free"},
        {"id": "t8", "number": 2, "status": "reserved"},
        {"id": "t9", "number": 3, "status": "free"},
    ],
}

# API Endpointi

@app.get("/api/clubs")
def get_clubs():
    return jsonify({"clubs": CLUBS})

@app.get("/api/clubs/<club_id>/events")
def get_events_for_club(club_id):
    events = [e for e in EVENTS if e["club_id"] == club_id]
    return jsonify({"events": events})

@app.get("/api/events/<event_id>/tables")
def get_tables_for_event(event_id):
    return jsonify({"tables": TABLES.get(event_id, [])})

@app.post("/api/events/<event_id>/tables/<table_id>/reserve")
def reserve_table(event_id, table_id):
    tables = TABLES.get(event_id, [])
    for t in tables:
        if t["id"] == table_id:
            if t["status"] == "reserved":
                return jsonify({"success": False, "message": "Stol je već zauzet"}), 409
            t["status"] = "reserved"
            return jsonify({"success": True, "table": t}), 201
    return jsonify({"success": False, "message": "Stol ne postoji"}), 404

@app.post("/api/events/<event_id>/tables/<table_id>/cancel")
def cancel_table(event_id, table_id):
    tables = TABLES.get(event_id, [])
    for t in tables:
        if t["id"] == table_id:
            if t["status"] == "free":
                return jsonify({"success": False, "message": "Stol je već slobodan"}), 409
            t["status"] = "free"
            return jsonify({"success": True, "table": t}), 200
    return jsonify({"success": False, "message": "Stol ne postoji"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
