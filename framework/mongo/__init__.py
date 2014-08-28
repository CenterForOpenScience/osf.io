# -*- coding: utf-8 -*-

from pymongo import MongoClient
from bson import ObjectId

from modularodm import FlaskStoredObject as StoredObject

from website import settings

mongo_uri = 'mongodb://localhost:{port}'.format(port=settings.DB_PORT)
client = MongoClient(mongo_uri)

db = client[settings.DB_NAME]

if settings.DB_USER and settings.DB_PASS:
    db.authenticate(settings.DB_USER, settings.DB_PASS)


def set_up_storage(schemas, storage_class, prefix='', addons=None, *args, **kwargs):
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
    # import pdb; pdb.set_trace()
    _schemas = []
    _schemas.extend(schemas)

    for addon in (addons or []):
        _schemas.extend(addon.models)

    for schema in _schemas:
        collection = "{0}{1}".format(prefix, schema._name)
        schema.set_storage(storage_class(collection=collection, **kwargs))
    return None

