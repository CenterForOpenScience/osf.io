import os
import urllib
import uuid

from pymongo import MongoClient
import requests

from framework.mongo.utils import to_mongo_key

from website import settings
from website.addons.wiki import settings as wiki_settings


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


def delete_share_doc(node, wname):
    """Deletes share document and removes namespace from model."""

    db = share_db()
    sharejs_uuid = get_sharejs_uuid(node, wname)

    db['docs'].remove({'_id': sharejs_uuid})
    db['docs_ops'].remove({'name': sharejs_uuid})

    wiki_key = to_mongo_key(wname)
    del node.wiki_private_uuids[wiki_key]
    node.save()


def migrate_uuid(node, wname):
    """Migrates uuid to new namespace."""

    db = share_db()
    old_sharejs_uuid = get_sharejs_uuid(node, wname)

    broadcast_to_sharejs('lock', old_sharejs_uuid)

    generate_private_uuid(node, wname)
    new_sharejs_uuid = get_sharejs_uuid(node, wname)

    doc_item = db['docs'].find_one({'_id': old_sharejs_uuid})
    if doc_item:
        doc_item['_id'] = new_sharejs_uuid
        db['docs'].insert(doc_item)
        db['docs'].remove({'_id': old_sharejs_uuid})

    ops_items = [item for item in db['docs_ops'].find({'name': old_sharejs_uuid})]
    if ops_items:
        for item in ops_items:
            item['_id'] = item['_id'].replace(old_sharejs_uuid, new_sharejs_uuid)
            item['name'] = new_sharejs_uuid
        db['docs_ops'].insert(ops_items)
        db['docs_ops'].remove({'name': old_sharejs_uuid})

    broadcast_to_sharejs('unlock', old_sharejs_uuid)


def share_db():
    """Generate db client for sharejs db"""
    client = MongoClient(settings.DB_HOST, settings.DB_PORT)
    return client[wiki_settings.SHAREJS_DB_NAME]


def get_sharejs_content(node, wname):
    db = share_db()
    sharejs_uuid = get_sharejs_uuid(node, wname)

    doc_item = db['docs'].find_one({'_id': sharejs_uuid})
    return doc_item['_data'] if doc_item else ''


def broadcast_to_sharejs(action, sharejs_uuid, node=None, wiki_name='home'):
    """
    Broadcast an action to all documents connected to a wiki.
    Actions include 'lock', 'unlock', 'redirect', and 'delete'
    'redirect' and 'delete' both require a node to be specified
    """

    url = 'http://{host}:{port}/{action}/{id}/'.format(
        host=wiki_settings.SHAREJS_HOST,
        port=wiki_settings.SHAREJS_PORT,
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

    try:
        requests.post(url)
    except requests.ConnectionError:
        pass    # Assume sharejs is not online
