import uuid
from pymongo import MongoClient

from framework.mongo.utils import to_mongo_key
from website import settings


def generate_share_uuid(node, wname):
    """Generate uuid for use in sharejs namespacing"""

    share_uuid = str(uuid.uuid1())
    wiki_key = to_mongo_key(wname)
    node.wiki_sharejs_uuids[wiki_key] = share_uuid
    node.save()

    return share_uuid


def to_mongo_uuid(node, share_uuid):
    """
    Format sharejs uuid into the form used in mongo.
    This is also the form passed to sharejs to open the sharejs doc, which
    includes node's primary ID to prevent fork namespace collision
    """
    return str(uuid.uuid5(uuid.UUID(share_uuid), str(node._id)))


def share_db():
    """Generate db client for sharejs db"""
    client = MongoClient(settings.DB_HOST, settings.DB_PORT)
    return client[settings.SHAREJS_DB_NAME]