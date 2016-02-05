# -*- coding: utf-8 -*-

import logging
import threading

import pymongo
from flask import g
from werkzeug.local import LocalProxy

from website import settings


logger = logging.getLogger(__name__)


class ClientPool(object):

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
        self._cache.append(self._local.pop(_id or self.thread_id))
        self._sem.release()

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

def get_mongo_client():
    """Create MongoDB client and authenticate database.
    """
    return CLIENT_POOL.acquire()


def connection_before_request():
    """Attach MongoDB client to `g`.
    """
    g._mongo_client = get_mongo_client()


def connection_teardown_request(error=None):
    """Close MongoDB client if attached to `g`.
    """
    if getattr(g, '_mongo_client', None):
        CLIENT_POOL.release()
        g._mongo_client = None


handlers = {
    'before_request': connection_before_request,
    'teardown_request': connection_teardown_request,
}


# Set up getters for `LocalProxy` objects
_mongo_client = get_mongo_client()


def _get_current_client():
    """Getter for `client` proxy. Return default client if no client attached
    to `g` or no request context.
    """
    return get_mongo_client()


def _get_current_database():
    """Getter for `database` proxy.
    """
    return _get_current_client()[settings.DB_NAME]


# Set up `LocalProxy` objects
client = LocalProxy(_get_current_client)
database = LocalProxy(_get_current_database)


def set_up_storage(schemas, storage_class, prefix='', addons=None, **kwargs):
    '''Setup the storage backend for each schema in ``schemas``.
    note::
        ``**kwargs`` are passed to the constructor of ``storage_class``

    Example usage with modular-odm and pymongo:
    ::

        >>> from pymongo import MongoClient
        >>> from modularodm.storage import MongoStorage
        >>> from models import User, Node, Tag
        >>> client = MongoClient(port=20771)
        >>> db = client['mydb']
        >>> models = [User, Node, Tag]
        >>> set_up_storage(models, MongoStorage)
    '''
    _schemas = []
    _schemas.extend(schemas)

    for addon in (addons or []):
        _schemas.extend(addon.models)

    for schema in _schemas:
        collection = '{0}{1}'.format(prefix, schema._name)
        schema.set_storage(
            storage_class(
                db=database,
                collection=collection,
                **kwargs
            )
        )
        # Allow models to define extra indices
        for index in getattr(schema, '__indices__', []):
            database[collection].ensure_index(**index)
