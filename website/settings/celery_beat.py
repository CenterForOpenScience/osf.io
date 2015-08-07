from celery.schedules import crontab


# Setting up a scheduler appended in app.py
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
