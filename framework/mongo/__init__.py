from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.dbref import DBRef

from website import settings
from urlparse import urlsplit

client = MongoClient(settings.mongo_uri)

db_name = urlsplit(settings.mongo_uri).path[1:] # Slices off the leading slash of the path (database name)

db = client[db_name]
