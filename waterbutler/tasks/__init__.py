from celery import Celery

from waterbutler import settings


app = Celery()
app.config_from_object(settings)
