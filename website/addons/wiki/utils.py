import uuid
from pymongo import MongoClient

from framework.mongo.utils import to_mongo_key
from website import settings


def generate_sharejs_uuid(node, wname):
    """Generate uuid for use in sharejs namespacing"""

    sharejs_uuid = str(uuid.uuid1())
    wiki_key = to_mongo_key(wname)
    node.wiki_sharejs_uuids[wiki_key] = sharejs_uuid
    node.save()

    return sharejs_uuid


def get_mongo_uuid(node, wname):
    """
    Format sharejs uuid into the form used in mongo.
    This is also the form passed to sharejs to open the sharejs doc, which
    includes node's primary ID to prevent fork namespace collision
    """
    wiki_key = to_mongo_key(wname)
    sharejs_uuid = node.wiki_sharejs_uuids.get(wiki_key)
    return str(uuid.uuid5(
        uuid.UUID(sharejs_uuid),
        str(node._id)
    )) if sharejs_uuid else None


def share_db():
    """Generate db client for sharejs db"""
    client = MongoClient(settings.DB_HOST, settings.DB_PORT)
    return client[settings.SHAREJS_DB_NAME]