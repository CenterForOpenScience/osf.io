import functools
import hashlib
import logging
import threading

import binascii
from collections import OrderedDict
import os

from celery.canvas import Signature
from celery.local import PromiseProxy
from gevent.pool import Pool
from flask import current_app, has_app_context

from website import settings

_local = threading.local()
logger = logging.getLogger(__name__)

def postcommit_queue():
    if not hasattr(_local, 'postcommit_queue'):
        _local.postcommit_queue = OrderedDict()
    return _local.postcommit_queue

def postcommit_celery_queue():
    if not hasattr(_local, 'postcommit_celery_queue'):
        _local.postcommit_celery_queue = OrderedDict()
    return _local.postcommit_celery_queue

def postcommit_before_request():
    logger.warning('Initializing postcommit queues before request')
    _local.postcommit_queue = OrderedDict()
    _local.postcommit_celery_queue = OrderedDict()

def postcommit_after_request(response, base_status_error_code=500):
    logger.warning(f'Postcommit after request triggered with status code {response.status_code}')
    if response.status_code >= base_status_error_code:
        logger.warning('Clearing postcommit queues due to error response')
        _local.postcommit_queue = OrderedDict()
        _local.postcommit_celery_queue = OrderedDict()
        return response
    try:
        if postcommit_queue():
            logger.warning(f'Processing postcommit_queue with {len(postcommit_queue())} tasks')
            number_of_threads = 30  # one db connection per greenlet, let's share
            pool = Pool(number_of_threads)
            for func in postcommit_queue().values():
                logger.warning(f'Spawning task {func}')
                pool.spawn(func)
            pool.join(timeout=5.0, raise_error=True)  # 5 second timeout and reraise exceptions

        if postcommit_celery_queue():
            logger.warning(f'Processing postcommit_celery_queue with {len(postcommit_celery_queue())} tasks')
            if settings.USE_CELERY:
                for task_dict in postcommit_celery_queue().values():
                    task = Signature.from_dict(task_dict)
                    logger.warning(f'Applying async task {task}')
                    task.apply_async()
            else:
                for task in postcommit_celery_queue().values():
                    logger.warning(f'Executing task {task}')

    except AttributeError as ex:
        logger.error(f'Post commit task queue not initialized: {ex}')
    except Exception as ex:
        logger.error(f'Exception during postcommit processing: {ex}')
    return response

def enqueue_postcommit_task(fn, args, kwargs, celery=False, once_per_request=True):
    if has_app_context() and current_app.config.get('TESTING', False):
        fn(*args, **kwargs)
    else:
        raw = [fn.__name__, fn.__module__, args, kwargs]
        m = hashlib.md5()
        m.update('-'.join([x.__repr__() for x in raw]).encode())
        key = m.hexdigest()

        if not once_per_request:
            key = f'{key}:{binascii.hexlify(os.urandom(8))}'

        if celery and isinstance(fn, PromiseProxy):
            logger.warning(f'Enqueuing celery task {fn.__name__} with key {key}')
            postcommit_celery_queue().update({key: fn.si(*args, **kwargs)})
        else:
            logger.warning(f'Enqueuing task {fn.__name__} with key {key}')
            postcommit_queue().update({key: functools.partial(fn, *args, **kwargs)})

handlers = {
    'before_request': postcommit_before_request,
    'after_request': postcommit_after_request,
}

def run_postcommit(once_per_request=True, celery=False):
    def wrapper(func):
        if settings.DEBUG_MODE:
            return func

        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            logger.warning(f'Wrapping function {func.__name__} for postcommit')
            enqueue_postcommit_task(func, args, kwargs, celery=celery, once_per_request=once_per_request)
        return wrapped
    return wrapper
