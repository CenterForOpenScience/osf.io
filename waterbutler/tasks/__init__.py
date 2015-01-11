from celery import Celery

from waterbutler.tasks import settings


app = Celery()
app.config_from_object(settings)
