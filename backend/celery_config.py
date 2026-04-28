from celery.schedules import crontab

# Spajanje na RabbitMQ i backend za rezultate
broker_url = 'amqp://guest:guest@rabbitmq:5672//'
result_backend = 'rpc://'

# Definiranje periodičnih zadataka
beat_schedule = {
    'generate-daily-report-every-minute': {
        'task': 'tasks.generate_daily_report',
        'schedule': 60.0,
    },
    'run-data-pipeline-daily': {
        'task': 'tasks.run_data_pipeline',
        'schedule': 86400.0,  # jednom dnevno
    },
}

timezone = 'UTC'
