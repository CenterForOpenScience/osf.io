# -*- coding: utf-8 -*-
"""Attach callbacks to signals emitted by Celery. This module should only be
imported by Celery and is not used elsewhere in the application.
"""
import logging

from celery import signals

from framework.mongo import storage, set_up_storage, StoredObject
from website import models, settings

logger = logging.getLogger(__name__)


@signals.task_prerun.connect
@signals.task_postrun.connect
def clear_caches(*args, **kwargs):
    """Clear database cache before and after each task.
    """
    StoredObject._clear_caches()


@signals.worker_process_init.connect
def attach_models(*args, **kwargs):
    """Attach models to database collections on worker initialization.
    """
    if settings.USE_POSTGRES:
        logger.debug('Not setting storage backends because USE_POSTGRES = True')
        return
    set_up_storage(models.MODELS, storage.MongoStorage)
