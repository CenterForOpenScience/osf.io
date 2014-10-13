import uuid
from pymongo import MongoClient

from website import settings


def docs_uuid(node, share_uuid):
    """
    Format sharejs uuid into the form used in the docs collection.
    This is also the form passed to sharejs to open the sharejs doc, which
    includes node's primary ID to prevent fork namespace collision
    """
    return str(uuid.uuid5(uuid.UUID(share_uuid), str(node._id)))


def ops_uuid(node, share_uuid):
    """Format sharejs uuid into the form used in the ops.uuid collection"""
    share_uuid = docs_uuid(node, share_uuid)
    return 'ops.{0}'.format(share_uuid.replace('-', '%2D'))


def share_db():
    """Generate db client for sharejs db"""
    # TODO: Use local proxy
    client = MongoClient(settings.DB_HOST, settings.DB_PORT)
    return client.sharejs


def generate_share_uuid(node, wid):
    """Generate uuid for use in sharejs namespacing"""

    share_uuid = str(uuid.uuid1())
    node.wiki_sharejs_uuids[wid] = share_uuid
    node.save()

    return share_uuid
