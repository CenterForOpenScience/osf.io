from __future__ import absolute_import

from celery import Celery

# instansiate Celery object
celery = Celery()

# TODO: Hardcoded. Should be set using framework's config handler
celery.config_from_object('celeryconfig')

if __name__ == '__main__':
    celery.start()
