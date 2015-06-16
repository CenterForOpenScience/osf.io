# -*- coding: utf-8 -*-

from furl import furl
from datetime import datetime

from website.notifications.emails import notify, remove_users_from_subscription
from website.notifications.utils import move_file_subscription
from website.models import Node


def file_notify(user, node, event, payload):
    f_url = furl(node.absolute_url)
    event_options = {
        'file_added': lambda: file_created(node, f_url, payload),
        'file_updated': lambda: file_updated(node, f_url, payload),
        'file_removed': lambda: file_deleted(node, f_url, payload),
        'folder_created': lambda: folder_added(node, f_url, payload),
        'addon_file_moved': lambda: file_moved(node, f_url, payload, user),
        'addon_file_copied': lambda: file_copied(node, f_url, payload)
    }
    event_sub, f_url, message = event_options[event]()
    timestamp = datetime.utcnow()

    notify(
        uid=node._id,
        event=event_sub,
        user=user,
        node=node,
        timestamp=timestamp,
        message=message,
        gravatar_url=user.gravatar_url,
        url=f_url.url
    )


def file_info(node, path, provider):
    addon = node.get_addon(provider)
    file_guid, created = addon.find_or_create_file_guid(path if path.startswith('/') else '/' + path)
    return file_guid, file_guid.guid_url.strip('/') + "_file_updated", file_guid.guid_url


def file_created(node, f_url, payload):
    file_guid, event_sub, f_url.path = file_info(node, path=payload['metadata']['path'], provider=payload['provider'])
    file_name = payload['metadata']['materialized'].strip("/")
    message = 'added file "<b>{}</b>".'.format(file_name)
    return event_sub, f_url, message


def file_updated(node, f_url, payload):
    file_guid, event_sub, f_url.path = file_info(node, path=payload['metadata']['path'], provider=payload['provider'])
    file_name = payload['metadata']['materialized'].strip("/")
    message = 'updated file "<b>{}</b>".'.format(file_name)
    return event_sub, f_url, message


def file_deleted(node, f_url, payload):
    event_sub = "file_updated"
    f_url.path = node.web_url_for('collect_file_trees')
    file_name = payload['metadata']['materialized'].strip("/")
    message = 'removed file "<b>{}</b>".'.format(file_name)
    return event_sub, f_url, message


def folder_added(node, f_url, payload):
    event_sub = "file_updated"
    f_url.path = node.web_url_for('collect_file_trees')
    folder_name = payload['metadata']['materialized'].strip("/")
    message = 'created folder "<b>{}</b>".'.format(folder_name)
    return event_sub, f_url, message


def file_moved(node, f_url, payload, user):
    file_guid, event_sub, f_url.path = file_info(node, path=payload['destination']['path'],
                                                 provider=payload['destination']['provider'])
    # WB path does NOT change with moving.
    old_node = Node.load(payload['source']['node']['_id'])
    old_guid, old_sub, old_path = file_info(old_node, payload['destination']['path'],
                                            payload['source']['provider'])
    if file_guid != old_guid:
        rm_url = f_url
        rm_url.path = node.web_url_for('collect_file_trees')
        rm_users = move_file_subscription(old_sub, payload['source']['node']['_id'],
                                          event_sub, node)
        remove_users_from_subscription(rm_users, old_sub, user, old_node, timestamp=None,
                                       gravatar_url=user.gravatar_url, message="Removed", url=rm_url)
    message = 'moved "<b>{}</b>" from {} in {} to "<b>{}</b>" in {} in {}.'.format(
        payload['source']['materialized'], payload['source']['addon'], payload['source']['node']['title'],
        payload['destination']['materialized'], payload['destination']['addon'],
        payload['destination']['node']['title']
    )
    return event_sub, f_url, message


def file_copied(node, f_url, payload):
    file_guid, event_sub, f_url.path = file_info(node, path=payload['destination']['path'],
                                                 provider=payload['destination']['provider'])
    # TODO: send subscription to old sub guid. Should not have a sub for the new one.
    # WB path CHANGES
    old_guid, old_sub, old_path = file_info(Node.load(payload['source']['node']['_id']),
                                            payload['destination']['path'],
                                            payload['source']['provider'])
    message = 'copied "<b>{}</b>" from {} in {} to "<b>{}</b>" in {} in {}.'.format(
        payload['source']['materialized'], payload['source']['addon'], payload['source']['node']['title'],
        payload['destination']['materialized'], payload['destination']['addon'],
        payload['destination']['node']['title']
    )
    return event_sub, f_url, message
