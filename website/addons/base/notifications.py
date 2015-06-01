# -*- coding: utf-8 -*-

from furl import furl
from datetime import datetime

from website.notifications.emails import notify
from website.notifications.utils import move_file_subscription
from website.models import Node


def file_notify(user, node, event, payload):
    f_url = furl(node.absolute_url)
    event_options = {
        'file_added': file_created,
        'file_updated': file_updated,
        'file_removed': file_deleted,
        'folder_created': folder_added,
        'addon_file_moved': file_moved,
        'addon_file_copied': file_copied
    }
    event_sub, f_url, message = event_options[event](node, f_url, payload)
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
    message = 'added file "<strong>{}{}</strong>".'.format(payload['provider'],
                                                           payload['metadata']['materialized'])
    return event_sub, f_url, message


def file_updated(node, f_url, payload):
    file_guid, event_sub, f_url.path = file_info(node, path=payload['metadata']['path'], provider=payload['provider'])
    message = 'updated file "<strong>{}{}</strong>".'.format(payload['provider'],
                                                             payload['metadata']['materialized'])
    return event_sub, f_url, message


def file_deleted(node, f_url, payload):
    event_sub = "file_updated"
    f_url.path = node.web_url_for('collect_file_trees')
    message = 'deleted file "<strong>{}</strong>".'.format(payload['metadata']['materialized'])
    return event_sub, f_url, message


def folder_added(node, f_url, payload):
    event_sub = "file_updated"
    f_url.path = node.web_url_for('collect_file_trees')
    message = 'added folder "<strong>{}{}</strong>".'.format(payload['provider'],
                                                             payload['metadata']['materialized'])
    return event_sub, f_url, message


def file_moved(node, f_url, payload):
    file_guid, event_sub, f_url.path = file_info(node, path=payload['destination']['path'],
                                                 provider=payload['destination']['provider'])
    # WB path does NOT change with moving.
    old_guid, old_sub, old_path = file_info(Node.load(payload['source']['node']['_id']),
                                            payload['destination']['path'],
                                            payload['source']['provider'])
    if file_guid != old_guid:
        move_file_subscription(old_sub, payload['source']['node']['_id'],
                               event_sub, node)
    message = 'moved "<strong>{}</strong>" from "<strong>{}/{}{}</strong>" to "<strong>{}/{}/{}</strong>".'.format(
        payload['destination']['name'],
        payload['source']['node']['title'], payload['source']['provider'], payload['source']['materialized'],
        payload['destination']['node']['title'], payload['destination']['provider'],
        payload['destination']['materialized']
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
    message = 'copied "<strong>{}</strong>" from "<strong>{}/{}{}</strong>" to "<strong>{}/{}/{}</strong>".'.format(
        payload['destination']['name'],
        payload['source']['node']['title'], payload['source']['provider'], payload['source']['materialized'],
        payload['destination']['node']['title'], payload['destination']['provider'],
        payload['destination']['materialized']
    )
    return event_sub, f_url, message
