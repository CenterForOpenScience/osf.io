# -*- coding: utf-8 -*-
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
    _local.postcommit_queue = OrderedDict()
    _local.postcommit_celery_queue = OrderedDict()

def postcommit_after_request(response, base_status_error_code=500):
    if response.status_code >= base_status_error_code:
        _local.postcommit_queue = OrderedDict()
        _local.postcommit_celery_queue = OrderedDict()
        return response
    try:
        if postcommit_queue():
            number_of_threads = 30  # one db connection per greenlet, let's share
            pool = Pool(number_of_threads)
            for func in postcommit_queue().values():
                pool.spawn(func)
            pool.join(timeout=5.0, raise_error=True)  # 5 second timeout and reraise exceptions

        if postcommit_celery_queue():
            if settings.USE_CELERY:
                for task_dict in postcommit_celery_queue().values():
                    task = Signature.from_dict(task_dict)
                    task.apply_async()
            else:
                for task in postcommit_celery_queue().values():
                    task()

    except AttributeError as ex:
        if not settings.DEBUG_MODE:
            logger.error('Post commit task queue not initialized: {}'.format(ex))
    return response

def get_task_from_postcommit_queue(name, predicate):
    matches = [task for key, task in postcommit_celery_queue().iteritems() if task.type.name == name and predicate(task)]
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        raise ValueError()
    return False

def enqueue_postcommit_task(fn, args, kwargs, celery=False, once_per_request=True):
    '''
    Any task queued with this function where celery=True will be run asynchronously.
    '''
    # make a hash of the pertinent data
    raw = [fn.__name__, fn.__module__, args, kwargs]
    m = hashlib.md5()
    m.update('-'.join([x.__repr__() for x in raw]))
    key = m.hexdigest()

    if not once_per_request:
        # we want to run it once for every occurrence, add a random string
        key = '{}:{}'.format(key, binascii.hexlify(os.urandom(8)))

    if celery and isinstance(fn, PromiseProxy):
        postcommit_celery_queue().update({key: fn.si(*args, **kwargs)})
    else:
        postcommit_queue().update({key: functools.partial(fn, *args, **kwargs)})

handlers = {
    'before_request': postcommit_before_request,
    'after_request': postcommit_after_request,
}

def run_postcommit(once_per_request=True, celery=False):
    '''
    Delays function execution until after the request's transaction has been committed.
    If you set the celery kwarg to True args and kwargs must be JSON serializable
    Tasks will only be run if the response's status code is < 500.
    Any task queued with this function where celery=True will be run asynchronously.
    :return:
    '''
    def wrapper(func):
        # if we're local dev or running unit tests, run without queueing
        if settings.DEBUG_MODE:
            return func
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            enqueue_postcommit_task(func, args, kwargs, celery=celery, once_per_request=once_per_request)
        return wrapped
    return wrapper
