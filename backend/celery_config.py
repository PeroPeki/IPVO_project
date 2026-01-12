from celery.schedules import crontab

# Spajanje na RabbitMQ i backend za rezultate
broker_url = 'amqp://guest:guest@rabbitmq:5672//'
result_backend = 'rpc://'

# Definiranje periodičnih zadataka
beat_schedule = {
    'generate-daily-report-every-minute': { # Ime zadatka
        'task': 'tasks.generate_daily_report', # Pozivana funkcija
        'schedule': 60.0, # Svakih 60 sekundi
    },
}

timezone = 'UTC'
