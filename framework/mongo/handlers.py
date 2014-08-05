# -*- coding: utf-8 -*-

import logging
from flask import g
from pymongo import MongoClient
from werkzeug.local import LocalProxy

from website import settings


logger = logging.getLogger(__name__)


def get_mongo_client():

    mongo_uri = 'mongodb://localhost:{port}'.format(port=settings.DB_PORT)
    client = MongoClient(mongo_uri)

    db = client[settings.DB_NAME]

    if settings.DB_USER and settings.DB_PASS:
        db.authenticate(settings.DB_USER, settings.DB_PASS)

    return client


def connection_before_request():
    g._mongo_client = get_mongo_client()


def connection_teardown_request(error=None):
    try:
        g._mongo_client.close()
    except AttributeError:
        if not settings.DEBUG_MODE:
            logger.error('MongoDB client not attached to request.')


def add_database_handlers(app):
    """

    """
    app.before_request(connection_before_request)
    app.teardown_request(connection_teardown_request)


# Getters for `LocalProxy` objects
_mongo_client = get_mongo_client()


def _get_current_client():
    try:
        return g._mongo_client
    except (AttributeError, RuntimeError):
        return _mongo_client


def _get_current_database():
    return _get_current_client()[settings.DB_NAME]

# `LocalProxy` objects
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
        >>> from models import User, ApiKey, Node, Tag
        >>> client = MongoClient(port=20771)
        >>> db = client['mydb']
        >>> models = [User, ApiKey, Node, Tag]
        >>> set_up_storage(models, MongoStorage, db=db)
    '''
    _schemas = []
    _schemas.extend(schemas)

    for addon in (addons or []):
        _schemas.extend(addon.models)

    for schema in _schemas:
        collection = '{0}{1}'.format(prefix, schema._name)
        schema.set_storage(
            storage_class(
                client=client,
                database=kwargs.pop('database', None) or settings.DB_NAME,
                collection=collection,
                **kwargs
            )
        )
