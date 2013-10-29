from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.dbref import DBRef

from website import settings
from urlparse import urlsplit

client = MongoClient(settings.MONGO_URI)

db_name = urlsplit(settings.MONGO_URI).path[1:] # Slices off the leading slash of the path (database name)

db = client[db_name]

def set_up_storage(schemas, storage_class, prefix='', *args, **kwargs):
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
    for schema in schemas:
        collection = "{0}{1}".format(prefix, schema._name)
        schema.set_storage(storage_class(collection=collection, **kwargs))
    return None
