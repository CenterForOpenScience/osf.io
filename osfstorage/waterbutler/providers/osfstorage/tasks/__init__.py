from celery import Celery

from waterbutler.providers.osfstorage import settings


app = Celery()
app.config_from_object(settings)
