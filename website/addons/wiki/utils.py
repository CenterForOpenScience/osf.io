import os
import urllib
import uuid

from pymongo import MongoClient
import requests

from framework.mongo.utils import to_mongo_key
from website import settings


def generate_private_uuid(node, wname):
    """Generate private uuid for use in sharejs namespacing"""

    private_uuid = str(uuid.uuid1())
    wiki_key = to_mongo_key(wname)
    node.wiki_private_uuids[wiki_key] = private_uuid
    node.save()

    return private_uuid


def get_sharejs_uuid(node, wname):
    """
    Format private uuid into the form used in mongo and sharejs.
    This includes node's primary ID to prevent fork namespace collision
    """
    wiki_key = to_mongo_key(wname)
    private_uuid = node.wiki_private_uuids.get(wiki_key)
    return str(uuid.uuid5(
        uuid.UUID(private_uuid),
        str(node._id)
    )) if private_uuid else None


def share_db():
    """Generate db client for sharejs db"""
    client = MongoClient(settings.DB_HOST, settings.DB_PORT)
    return client[settings.SHAREJS_DB_NAME]


def broadcast_to_sharejs(action, sharejs_uuid, node=None, wiki_name='home'):
    """
    Broadcast an action to all documents connected to a wiki.
    Actions include 'lock', 'unlock', 'redirect', and 'delete'
    'redirect' and 'delete' both require a node to be specified
    """

    url = 'http://{host}:{port}/{action}/{id}/'.format(
        host=settings.SHAREJS_HOST,
        port=settings.SHAREJS_PORT,
        action=action,
        id=sharejs_uuid
    )

    if action == 'redirect' or action == 'delete':
        page = 'project_wiki_edit' if action == 'redirect' else 'project_wiki_page'
        redirect_url = urllib.quote(
            node.web_url_for(page, wname=wiki_name, _guid=True),
            safe='',
        )
        url = os.path.join(url, redirect_url)

    requests.post(url)