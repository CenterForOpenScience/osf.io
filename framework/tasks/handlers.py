# -*- coding: utf-8 -*-

import logging
import functools

from celery import group

from framework.tasks import queue

from website import settings


logger = logging.getLogger(__name__)


def celery_before_request():
    global queue
    queue = []  # noqa


def celery_teardown_request(error=None):
    global queue
    if error is not None:
        return
    try:
        if queue:
            if settings.USE_CELERY:
                group(queue).apply_async()
            else:
                for task in queue:
                    task.apply()
    except AttributeError:
        if not settings.DEBUG_MODE:
            logger.error('Task queue not initialized')


def enqueue_task(signature):
    global queue
    """If working in a request context, push task signature to ``g`` to run
    after request is complete; else run signature immediately.
    :param signature: Celery task signature
    """
    try:
        if signature not in queue:
            queue.append(signature)
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
