from flask import Flask, jsonify
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
