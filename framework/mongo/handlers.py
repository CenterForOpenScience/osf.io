# -*- coding: utf-8 -*-

import logging
import threading

import pymongo
from pymongo.errors import ConnectionFailure
from website import settings
from werkzeug.local import LocalProxy

logger = logging.getLogger(__name__)


class ClientPool(object):

    class ExtraneousReleaseError(Exception):
        message = 'no cached connection to release'

    @property
    def thread_id(self):
        return threading.current_thread().ident

    def __init__(self, MAX_CLIENTS=100):
        self._max_clients = MAX_CLIENTS
        self._cache, self._local = [], {}
        self._sem = threading.BoundedSemaphore(MAX_CLIENTS)

    def acquire(self, _id=None):
        _id = _id or self.thread_id

        if _id not in self._local:
            self._sem.acquire()
            self._local[_id] = self._get_client()
        return self._local[_id]

    def release(self, _id=None):
        try:
            self._cache.append(self._local.pop(_id or self.thread_id))
            self._sem.release()
        except KeyError:
            raise ClientPool.ExtraneousReleaseError

    def transfer(self, to, from_):
        self._local[to] = self._local.pop(from_ or self.thread_id)

    def _get_client(self):
        try:
            return self._cache.pop(0)
        except IndexError:
            pass
        logger.warning('Creating new client instance. {} instances initialized.'.format(self._max_clients - self._sem._Semaphore__value))
        client = pymongo.MongoClient(settings.DB_HOST, settings.DB_PORT, max_pool_size=1)
        db = client[settings.DB_NAME]

        if settings.DB_USER and settings.DB_PASS:
            db.authenticate(settings.DB_USER, settings.DB_PASS)
        return client


CLIENT_POOL = ClientPool()

def _get_current_client():
    """Get the current mongodb client from the pool.
    """
    if settings.USE_POSTGRES:
        return None
    return CLIENT_POOL.acquire()


def _get_current_database():
    """Getter for `database` proxy.
    """
    if settings.USE_POSTGRES:
        return None
    try:
        return _get_current_client()[settings.DB_NAME]
    except ConnectionFailure:
        if settings.DEBUG_MODE:
            logger.warn('Cannot connect to database.')
            return None
        else:
            raise

# Set up `LocalProxy` objects
client = LocalProxy(_get_current_client)
database = LocalProxy(_get_current_database)
