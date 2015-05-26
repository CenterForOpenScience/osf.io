# -*- coding: utf-8 -*-

from furl import furl
from datetime import datetime

from website.models import Guid
from website.notifications.emails import notify


def file_notify(user, node, event, payload):
    f_url = furl(node.absolute_url)
    event_options = {
        'file_added': file_created,
        'file_updated': file_updated,
        'file_removed': file_deleted,
        'create_folder': folder_added,
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
    return file_guid


def file_created(node, f_url, payload):
    file_guid = file_info(node, path=payload['metadata']['path'], provider=payload['provider'])
    event_sub = file_guid.guid_url.strip('/') + "_file_updated"
    f_url.path = file_guid.guid_url
    message = 'added file "<strong>{}{}</strong>".'.format(payload['provider'],
                                                           payload['metadata']['materialized'])
    return event_sub, f_url, message


def file_updated(node, f_url, payload):
    file_guid = file_info(node, path=payload['metadata']['path'], provider=payload['provider'])
    event_sub = file_guid.guid_url.strip('/') + "_file_updated"
    f_url.path = file_guid.guid_url
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
    file_guid = file_info(node, path=payload['destination']['path'],
                          provider=payload['destination']['provider'])
    event_sub = file_guid.guid_url.strip('/') + "_file_updated"
    f_url.path = file_guid.guid_url
    # TODO: Copy subscription to new guid
    message = 'moved "<strong>{}</strong>" from "<strong>{}/{}{}</strong>" to "<strong>{}/{}/{}</strong>".'.format(
        payload['destination']['name'],
        payload['source']['node']['title'], payload['source']['provider'], payload['source']['materialized'],
        payload['destination']['node']['title'], payload['destination']['provider'],
        payload['destination']['materialized']
    )
    return event_sub, f_url, message


def file_copied(node, f_url, payload):
    file_guid = file_info(node, path=payload['destination']['path'],
                          provider=payload['destination']['provider'])
    event_sub = file_guid.guid_url.strip('/') + "_file_updated"
    f_url.path = file_guid.guid_url
    # TODO: send subscription to old sub guid.
    message = 'copied "<strong>{}</strong>" from "<strong>{}/{}{}</strong>" to "<strong>{}/{}/{}</strong>".'.format(
        payload['destination']['name'],
        payload['source']['node']['title'], payload['source']['provider'], payload['source']['materialized'],
        payload['destination']['node']['title'], payload['destination']['provider'],
        payload['destination']['materialized']
    )
    return event_sub, f_url, message
