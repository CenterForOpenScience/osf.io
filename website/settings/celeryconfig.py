from celery.schedules import crontab


##### Celery #####
## Default RabbitMQ broker
BROKER_URL = 'amqp://'

# Default RabbitMQ backend
CELERY_RESULT_BACKEND = 'amqp://'

# CELERYBEAT_SCHEDULE_FILENAME = 'celeryconfig.py'
# Setting up a scheduler, essentially replaces an
#  independent cronjob
CELERYBEAT_SCHEDULE = {
    '5-minute-emails': {
        'task': 'notify.send_users_email',
        'schedule': crontab(minute='*/5'),
        'args': ('email_transactional',),
    },
    'daily-emails': {
        'task': 'notify.send_users_email',
        'schedule': crontab(minute=0, hour=0),
        'args': ('email_digest',),
    },
}

# Modules to import when celery launches
CELERY_IMPORTS = (
    'framework.tasks',
    'framework.tasks.signals',
    'framework.email.tasks',
    'framework.analytics.tasks',
    'website.mailchimp_utils',
    'website.notifications.tasks',
    'website.archiver.tasks'
)
