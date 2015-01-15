from celery import Celery

from waterbutler import settings
from waterbutler.tasks import settings as tasks_settings

from raven import Client
from raven.contrib.celery import register_signal


app = Celery()
app.config_from_object(tasks_settings)


sentry_dsn = settings.get('SENTRY_DSN', None)
if sentry_dsn:
    client = Client(sentry_dsn)
    register_signal(client)
else:
    client = None
