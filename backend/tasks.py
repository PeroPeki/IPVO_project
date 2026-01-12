from celery import Celery
from pymongo import MongoClient
from datetime import datetime, timedelta

# Inicijalizacija Celery aplikacije
app = Celery('tasks')
app.config_from_object('celery_config')

# Funkcija za generiranje dnevnog izvještaja
@app.task
def generate_daily_report():
    print("Generiranje dnevnog izvještaja...")
    
    # Spajanje na MongoDB
    client = MongoClient("mongodb://mongo:27017")
    db = client["mydb"]
    
    # Analiza podataka iz kolekcija
    total_reservations = db.reservations.count_documents({})
    total_tickets = db.tickets.count_documents({})
    
    # Kreiranje izvještaja
    report = {
        "date": datetime.utcnow().isoformat(),
        "type": "DAILY_STATS",
        "metrics": {
            "total_reservations": total_reservations,
            "total_tickets_sold": total_tickets,
            "revenue_estimate": total_tickets * 10
        }
    }
    
    # Spremanje u novu kolekciju reports
    db.reports.insert_one(report)
    
    print(f"Izvještaj spremljen! ID: {report['_id']}")
    client.close()
