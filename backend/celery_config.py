# Redis kao broker i result backend (RabbitMQ je uklonjen iz sustava)
broker_url = 'redis://redis:6379/1'
result_backend = 'redis://redis:6379/2'

beat_schedule = {
    'daily-report': {
        'task': 'tasks.generate_daily_report',
        'schedule': 86400.0,
    },
    'reservation-reminders': {
        'task': 'tasks.send_reservation_reminders',
        'schedule': 3600.0,   # svakih sat vremena provjerava
    },
}

timezone = 'UTC'
