# -*- coding: utf-8 -*-

import logging
import threading
import functools

from celery import group

from website import settings


_local = threading.local()
logger = logging.getLogger(__name__)


def celery_before_request():
    _local.queue = []


def celery_teardown_request(error=None):
    if error is not None:
        return
    try:
        if _local.queue:
            if settings.USE_CELERY:
                group(_local.queue).apply_async()
            else:
                for task in _local.queue:
                    task.apply()
    except AttributeError:
        if not settings.DEBUG_MODE:
            logger.error('Task queue not initialized')


def enqueue_task(signature):
    """If working in a request context, push task signature to ``g`` to run
    after request is complete; else run signature immediately.
    :param signature: Celery task signature
    """
    try:
        if signature not in _local.queue:
            _local.queue.append(signature)
    except (RuntimeError):
        signature()


def queued_task(task):
    """Decorator that adds the wrapped task to the queue on ``g`` if Celery is
    enabled, else runs the task synchronously. Can only be applied to Celery
    tasks; should be used for all tasks fired within a request context that
    may write to the database to avoid race conditions.
    """
    @functools.wraps(task)
    def wrapped(*args, **kwargs):
        signature = task.si(*args, **kwargs)
        enqueue_task(signature)
    return wrapped


handlers = {
    'before_request': celery_before_request,
    'teardown_request': celery_teardown_request,
}
