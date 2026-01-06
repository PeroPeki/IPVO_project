from flask import Flask, jsonify, request   # >>> NEW (dodao request)
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

# Mongo connection (inside docker-compose network)
client = MongoClient("mongodb://mongo:27017")  # service name "mongo"
db = client["mydb"]

clubs_col = db["clubs"]
events_col = db["events"]
tables_col = db["tables"]
reservations_col = db["reservations"]


@app.get("/api/clubs")
def get_clubs():
    clubs = list(clubs_col.find({}, {"_id": 0}))
    return jsonify({"clubs": clubs})


# >>> NEW: dodaj klub
@app.post("/api/clubs")
def add_club():
    data = request.get_json()

    required = ["id", "name", "location", "description"]
    if not data or any(k not in data for k in required):
        return jsonify({"success": False, "message": "Nedostaju polja"}), 400

    # dodatna validacija ID-a
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



# >>> NEW: obriši klub
@app.delete("/api/clubs/<club_id>")
def delete_club(club_id):
    result = clubs_col.delete_one({"id": club_id})

    if result.deleted_count == 0:
        return jsonify({"success": False, "message": "Klub ne postoji"}), 404

    # opcionalno: obriši i sve vezano za klub
    events_col.delete_many({"club_id": club_id})
    tables_col.delete_many({"club_id": club_id})
    reservations_col.delete_many({"club_id": club_id})

    return jsonify({"success": True}), 200
# <<< NEW END


@app.get("/api/clubs/<club_id>/events")
def get_events_for_club(club_id):
    events = list(events_col.find({"club_id": club_id}, {"_id": 0}))
    return jsonify({"events": events})


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

    # (Opcionalno) označi zadnju rezervaciju kao canceled
    reservations_col.update_one(
        {"event_id": event_id, "table_id": table_id, "status": "booked"},
        {"$set": {"status": "canceled"}}
    )

    table["status"] = "free"
    return jsonify({"success": True, "table": table}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
