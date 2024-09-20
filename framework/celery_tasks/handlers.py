import logging
import threading
import functools

from celery import group
from flask import has_app_context

from api.base.api_globals import api_globals
from website import settings


_local = threading.local()
logger = logging.getLogger(__name__)


def queue():
    if not hasattr(_local, 'queue'):
        _local.queue = []
    return _local.queue


def celery_before_request():
    _local.queue = []


def celery_after_request(response, base_status_code_error=500):
    if response.status_code >= base_status_code_error:
        _local.queue = []
    return response


def celery_teardown_request(error=None):
    if error is not None:
        _local.queue = []
        return
    if queue():
        if settings.USE_CELERY:
            group(queue()).apply_async()
        else:
            for task in queue():
                task.apply()


def get_task_from_queue(name, predicate):
    matches = [task for task in queue() if task.type.name == name and predicate(task)]
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        raise ValueError()
    return False


# Wrapper function allows enqueue_task to be
# mock patched in a single location
def enqueue_task(signature):
    return _enqueue_task(signature)


def _enqueue_task(signature):
    """If working in a request context, push task signature to thread-local
    queue to run after request is complete; else run signature immediately.
    :param signature: Celery task signature
    """
    if (
        not has_app_context() and
        getattr(api_globals, 'request', None) is None
    ):  # Not in a request context
        signature.apply()
    else:
        if signature not in queue():
            queue().append(signature)


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
    'after_request': celery_after_request,
    'teardown_request': celery_teardown_request,
}
