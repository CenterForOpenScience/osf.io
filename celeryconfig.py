# Config file for Celery Daemon

# Default RabbitMQ broker
BROKER_URL = 'amqp://'

# Default RabbitMQ backend
CELERY_RESULT_BACKEND = 'amqp://'

# Modules to import when celery launches
CELERY_IMPORTS = (
    "framework.email.tasks",
    "framework.celery.tasks"
    )
