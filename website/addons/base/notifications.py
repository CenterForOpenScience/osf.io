# -*- coding: utf-8 -*-

from furl import furl
from datetime import datetime

from website.notifications.emails import notify, remove_users_from_subscription
from website.notifications.utils import move_file_subscription
from website.notifications.model import BaseNotification
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


def get_notify_type(user, node, event, payload):
    event_options = {
        'file_added': UpdateFileNotification,
        'file_updated': UpdateFileNotification,
        'file_removed': SimpleFileNotification,
        'folder_created': SimpleFileNotification,
        'addon_file_moved': MoveFileNotification,
        'addon_file_copied': MoveFileNotification
    }
    return event_options[event](user, node, event, payload)


class FileNotification(BaseNotification):
    """File notification base class"""

    def __init__(self, user, node, event, payload):
        super(FileNotification, self).__init__(user, node, event)
        self.payload = payload
        self.event_sub = None
        self.message = "Blank message"
        self.url = None
        self.guid = None

    @classmethod
    def unserialize(cls, user, node, event, payload):
        return get_notify_type(user, node, event, payload)

    def perform(self):
        notify(
            uid=self.node_id,
            event=self.event_sub,
            user=self.user,
            node=self.node,
            timestamp=self.timestamp,
            message=self.message,
            gravatar_url=self.gravatar_url,
            url=self.url
        )

    def form_message(self):
        f_type, action = tuple(self.event.split("_"))
        name = self.payload['metadata']['materialized'].strip('/')
        self.message = '{} {} "<b>{}</b>".'.format(action, f_type, name)

    def form_event(self):
        self.event_sub = "file_updated"

    def form_url(self):
        f_url = furl(self.node.absolute_url)
        return f_url

    def form_guid(self):
        addon = self.node.get_addon(self.payload['provider'])
        path = self.payload['metadata']['path']
        path = path if path.startswith('/') else '/' + path
        self.guid, created = addon.find_or_create_file_guid(path)


class UpdateFileNotification(FileNotification):
    """
    Class for simple file operations such as updating, adding files
    """
    def __init__(self, user, node, event, payload):
        super(UpdateFileNotification, self).__init__(user, node, event, payload)
        self.form_guid()
        self.form_event()
        self.form_message()
        self.form_url()

    def form_event(self):
        self.event_sub = self.guid.guid_url.strip('/') + '_file_updated'

    def form_url(self):
        f_url = super(UpdateFileNotification, self).form_url()
        f_url.path = self.guid.guid_url
        self.url = f_url.url


class SimpleFileNotification(FileNotification):
    """
    Class for file/folder operations that don't lead to a specific place
    """
    def __init__(self, user, node, event, payload):
        super(SimpleFileNotification, self).__init__(user, node, event, payload)
        self.form_event()
        self.form_message()
        self.form_url()

    def form_url(self):
        """Forms a url that points at the file view"""
        f_url = super(SimpleFileNotification, self).form_url()
        f_url.path = self.node.web_url_for('collect_file_trees')
        self.url = f_url.url


class MoveFileNotification(FileNotification):
    """
    Class for move and copy files. Users could be removed from subscription.
    """
    def __init__(self, user, node, event, payload):
        super(MoveFileNotification, self).__init__(user, node, event, payload)
        self.source_guid = None
        self.source_node = Node.load(self.payload['source']['node']['_id'])
        self.form_guid()
        self.source_event_sub = None
        self.form_event()
        self.source_url = None
        self.form_url()
        self.form_message()

    def perform(self):
        if 'moved' in self.event:
            rm_users = move_file_subscription(self.source_event_sub, self.source_node,
                                              self.event_sub, self.node)
            message = self.message + ' You have been removed due to insufficient permissions.',
            remove_users_from_subscription(rm_users, self.source_event_sub, self.user, self.source_node,
                                           timestamp=self.timestamp, gravatar_url=self.gravatar_url,
                                           message=message, url=self.source_url)
        else:
            self.message += ' You are not subscribed to the new file, follow link to add subscription.'
        super(MoveFileNotification, self).perform()

    def form_message(self):
        addon, f_type, action = tuple(self.event.split("_"))
        destination_name = self.payload['destination']['materialized'].strip('/')
        source_name = self.payload['source']['materialized'].strip('/')
        self.message = '{} "<b>{}</b>" from {} in {} to "<b>{}</b>" in {} in {}'.format(
            f_type, source_name, self.payload['source']['addon'], self.payload['source']['node']['title'],
            destination_name, self.payload['destination']['addon'], self.payload['destination']['node']['title']
        )

    def form_event(self):
        self.event_sub = self.guid.guid_url.strip('/') + '_file_updated'
        self.source_event_sub = self.source_guid.guid_url.strip('/') + '_file_updated'

    def form_url(self):
        f_url = super(MoveFileNotification, self).form_url()
        f_url.path = self.guid.guid_url
        self.url = f_url.url
        # source url
        if 'copied' in self.event:
            f_url.path = self.source_guid.guid_url
        else:
            f_url.path = self.node.web_url_for('collect_file_trees')
        self.source_url = f_url.url

    def form_guid(self):
        """Produces both guids"""
        addon = self.node.get_addon(self.payload['destination']['provider'])
        path = self.payload['destination']['path']
        path = path if path.startswith('/') else '/' + path
        self.guid, created = addon.find_or_create_file_guid(path)
        addon = self.source_node.get_addon(self.payload['source']['provider'])
        path = self.payload['source']['path']
        path = path if path.startswith('/') else '/' + path
        self.source_guid, created = addon.find_or_create_file_guid(path)
