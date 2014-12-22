from celery import Celery

from waterbutler.osfstorage import settings


app = Celery()
app.config_from_object(settings)
