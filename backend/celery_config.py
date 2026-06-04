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
    # Tjedno retreniranje — nedjelja u 3:00 ujutro generator, 4:00 trening
    'weekly-retrain-generate': {
        'task': 'tasks.run_generate_training_data',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),
    },
    'weekly-retrain-train': {
        'task': 'tasks.run_train_model',
        'schedule': crontab(hour=4, minute=0, day_of_week=0),
    },
}

timezone = 'UTC'
