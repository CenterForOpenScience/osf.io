# -*- coding: utf-8 -*-

import logging
import functools

from celery import group

from website import settings

logger = logging.getLogger(__name__)

def dynamic_import(module):
    parts = module.split('.')
    module = None
    while len(parts):
        if module:
            module = getattr(module, parts.pop(0))
        else:
            module = __import__(parts.pop(0))
    return module


def celery_before_request():
    thread_locals = dynamic_import(settings.THREAD_LOCALS)
    thread_locals._celery_tasks = []


def celery_teardown_request(error=None):
    thread_locals = dynamic_import(settings.THREAD_LOCALS)
    if error is not None:
        return
    try:
        tasks = thread_locals._celery_tasks
        if tasks:
            if settings.USE_CELERY:
                group(tasks).apply_async()
            else:
                for task in tasks:
                    task.apply()
    except AttributeError:
        if not settings.DEBUG_MODE:
            logger.error('Task queue not initialized')


def enqueue_task(signature):
    """If working in a request context, push task signature to the app's
    thread local variables to run after request is complete; else run
    signature immediately.
    :param signature: Celery task signature
    """
    thread_locals = dynamic_import(settings.THREAD_LOCALS)
    try:
        if signature not in thread_locals._celery_tasks:
            thread_locals._celery_tasks.append(signature)
    except RuntimeError:
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
