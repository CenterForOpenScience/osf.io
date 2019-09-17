# -*- coding: utf-8 -*-
import os
from future.moves.urllib.parse import quote
import uuid

import ssl
from pymongo import MongoClient
import requests
from bs4 import BeautifulSoup
from django.apps import apps

from addons.wiki import settings as wiki_settings
from addons.wiki.exceptions import InvalidVersionError
from osf.utils.permissions import ADMIN, READ, WRITE
# MongoDB forbids field names that begin with "$" or contain ".". These
# utilities map to and from Mongo field names.

mongo_map = {
    '.': '__!dot!__',
    '$': '__!dollar!__',
}

def to_mongo(item):
    for key, value in mongo_map.items():
        item = item.replace(key, value)
    return item

def to_mongo_key(item):
    return to_mongo(item).strip().lower()

def generate_private_uuid(node, wname):
    """
    Generate private uuid for internal use in sharejs namespacing.
    Note that this will NEVER be passed to to the client or sharejs.
    """

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

    write_contributors = [
        user._id for user in node.contributors
        if node.has_permission(user, WRITE)
    ]
    broadcast_to_sharejs('unlock', old_sharejs_uuid, data=write_contributors)


def share_db():
    """Generate db client for sharejs db"""
    client = MongoClient(wiki_settings.SHAREJS_DB_URL, ssl_cert_reqs=ssl.CERT_NONE)
    return client[wiki_settings.SHAREJS_DB_NAME]


def get_sharejs_content(node, wname):
    db = share_db()
    sharejs_uuid = get_sharejs_uuid(node, wname)

    doc_item = db['docs'].find_one({'_id': sharejs_uuid})
    return doc_item['_data'] if doc_item else ''


def broadcast_to_sharejs(action, sharejs_uuid, node=None, wiki_name='home', data=None):
    """
    Broadcast an action to all documents connected to a wiki.
    Actions include 'lock', 'unlock', 'redirect', and 'delete'
    'redirect' and 'delete' both require a node to be specified
    'unlock' requires data to be a list of contributors with write permission
    """

    url = 'http://{host}:{port}/{action}/{id}/'.format(
        host=wiki_settings.SHAREJS_HOST,
        port=wiki_settings.SHAREJS_PORT,
        action=action,
        id=sharejs_uuid
    )

    if action == 'redirect' or action == 'delete':
        redirect_url = quote(
            node.web_url_for('project_wiki_view', wname=wiki_name, _guid=True),
            safe='',
        )
        url = os.path.join(url, redirect_url)

    try:
        requests.post(url, json=data)
    except requests.ConnectionError:
        pass    # Assume sharejs is not online


def format_wiki_version(version, num_versions, allow_preview):
    """
    :param str version: 'preview', 'current', 'previous', '1', '2', ...
    :param int num_versions:
    :param allow_preview: True if view, False if compare
    """

    if not version:
        return

    if version.isdigit():
        version = int(version)
        if version > num_versions or version < 1:
            raise InvalidVersionError
        elif version == num_versions:
            return 'current'
        elif version == num_versions - 1:
            return 'previous'
    elif version != 'current' and version != 'previous':
        if allow_preview and version == 'preview':
            return version
        raise InvalidVersionError
    elif version == 'previous' and num_versions == 0:
        raise InvalidVersionError

    return version

def serialize_wiki_settings(user, nodes):
    """ Format wiki data for project settings page

    :param user: modular odm User object
    :param nodes: list of parent project nodes
    :return: treebeard-formatted data
    """
    WikiPage = apps.get_model('addons_wiki.WikiPage')

    items = []

    for node in nodes:
        assert node, '{} is not a valid Node.'.format(node._id)

        can_read = node.has_permission(user, READ)
        is_admin = node.has_permission(user, ADMIN)
        include_wiki_settings = WikiPage.objects.include_wiki_settings(node)

        if not include_wiki_settings:
            continue
        children = node.get_nodes(**{'is_deleted': False, 'is_node_link': False})
        children_tree = []

        wiki = node.get_addon('wiki')
        if wiki:
            children_tree.append({
                'select': {
                    'title': 'permission',
                    'permission':
                        'public'
                        if wiki.is_publicly_editable
                        else 'private'
                },
            })

        children_tree.extend(serialize_wiki_settings(user, children))

        item = {
            'node': {
                'id': node._id,
                'url': node.url if can_read else '',
                'title': node.title if can_read else 'Private Project',
                'is_public': node.is_public
            },
            'children': children_tree,
            'kind': 'folder' if not node.parent_node or not node.parent_node.has_permission(user, READ) else 'node',
            'nodeType': node.project_or_component,
            'category': node.category,
            'permissions': {
                'view': can_read,
                'admin': is_admin,
            },
        }

        items.append(item)

    return items


def serialize_wiki_widget(node):
    from addons.wiki.models import WikiVersion

    wiki = node.get_addon('wiki')
    wiki_version = WikiVersion.objects.get_for_node(node, 'home')

    # Show "Read more" link if there are multiple pages or has > 400 characters
    more = node.wikis.filter(deleted__isnull=True).count() >= 2
    MAX_DISPLAY_LENGTH = 400
    rendered_before_update = False
    if wiki_version and wiki_version.html(node):
        wiki_html = BeautifulSoup(wiki_version.html(node)).text
        if len(wiki_html) > MAX_DISPLAY_LENGTH:
            wiki_html = BeautifulSoup(wiki_html[:MAX_DISPLAY_LENGTH] + '...', 'html.parser')
            more = True

        rendered_before_update = wiki_version.rendered_before_update
    else:
        wiki_html = None

    wiki_widget_data = {
        'complete': True,
        'wiki_content': unicode(wiki_html) if wiki_html else None,
        'wiki_content_url': node.api_url_for('wiki_page_content', wname='home'),
        'rendered_before_update': rendered_before_update,
        'more': more,
        'include': False,
    }
    wiki_widget_data.update(wiki.config.to_json())
    return wiki_widget_data
