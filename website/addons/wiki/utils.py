from pymongo import MongoClient

from website import settings


def docs_uuid(node, share_uuid):
    """Format sharejs uuid into the form used in the docs collection"""
    return '{0}-{1}'.format(node._id, share_uuid)


def ops_uuid(node, share_uuid):
    """Format sharejs uuid into the form used in the ops.uuid collection"""
    share_uuid = docs_uuid(node, share_uuid)
    return 'ops.{0}'.format(share_uuid.replace('-', '%2D'))


def share_db():
    """Generate db client for sharejs db"""
    # TODO: Use domain and port
    client = MongoClient('localhost', settings.DB_PORT)
    return client.sharejs


def generate_share_uuid(node, wid):
    """Generate uuid for use in sharejs namespacing"""
    import uuid

    share_uuid = str(uuid.uuid5(uuid.uuid1(), str(wid)))
    node.wiki_sharejs_uuid[wid] = share_uuid
    node.save()

    return share_uuid
