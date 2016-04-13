import logging
import threading

import gevent

from website import settings

_local = threading.local()
logger = logging.getLogger(__name__)

def postcommit_queue():
    if not hasattr(_local, 'postcommit_queue'):
        _local.postcommit_queue = set()
    return _local.postcommit_queue

def postcommit_before_request():
    _local.postcommit_queue = set()

def postcommit_after_request(response, base_status_error_code=500):
    if response.status_code >= base_status_error_code:
        _local.postcommmit_queue = set()
        return response
    try:
        if postcommit_queue():
            threads = [gevent.spawn(func, *args) for func, args in postcommit_queue()]
            gevent.joinall(threads)
    except AttributeError:
        if not settings.DEBUG_MODE:
            logger.error('Post commit task queue not initialized')
    return response

def enqueue_postcommit_task(function_and_args):
    postcommit_queue().add(function_and_args)


handlers = {
    'before_request': postcommit_before_request,
    'after_request': postcommit_after_request,
}
