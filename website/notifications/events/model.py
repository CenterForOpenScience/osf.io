# -*- coding: utf-8 -*-
"""Basic Event handling for events that need subscriptions"""

from furl import furl
from datetime import datetime
from six import add_metaclass

from website.notifications.emails import warn_users_removed_from_subscription
from website.notifications.utils import move_file_subscription
from website.models import Node
from website.notifications.emails import notify


class EventMeta(type):
    def __init__(cls, name, bases, attrs):
        if not hasattr(cls, 'registry'):
            cls.registry = {}
        else:
            event_id = name.lower()
            cls.registry[event_id] = cls

        super(EventMeta, cls).__init__(name, bases, attrs)


@add_metaclass(EventMeta)
class Event(object):
    """
    Base notification class for building notification events and messages.
    - abstract methods set methods that must be defined by subclasses.
    """
    @classmethod
    def get_event(cls, user, node, event, **kwargs):
        kind = ''.join(event.split('_'))
        if kind in cls.registry:
            return cls.registry[kind](user, node, event, **kwargs)
        raise TypeError

    def perform(self):
        """Calls emails.notify"""
        notify(
            uid=self.node_id,
            event=self.event,
            user=self.user,
            node=self.node,
            timestamp=self.timestamp,
            message=self.message,
            gravatar_url=self.gravatar_url,
            url=self.url
        )

    def form_event(self):
        """
        Built from USER_SUBSCRIPTIONS_AVAILABLE, NODE_SUBSCRIPTIONS_AVAILABLE, and guids where applicable
        """
        raise NotImplementedError

    def form_message(self):
        """Piece together the message to be sent to subscribed users"""
        raise NotImplementedError

    def form_url(self):
        """Build url from relevant info"""
        raise NotImplementedError


class FileEvent(Event):
    """File event base class"""
    def __init__(self, user, node, event, payload=None):
        self.user = user
        self.gravatar_url = user.gravatar_url
        self.node = node
        self.node_id = node._id
        self.action = event
        self.timestamp = datetime.utcnow()
        self.event = event
        self.message = "Blank message"
        self.url = None
        self.payload = payload
        self.guid = None

    def form_message(self):
        f_type, action = tuple(self.action.split("_"))
        name = self.payload['metadata']['materialized'].strip('/')
        self.message = '{} {} "<b>{}</b>".'.format(action, f_type, name)

    def form_event(self):
        self.event = "file_updated"

    def form_url(self):
        f_url = furl(self.node.absolute_url)
        return f_url

    def form_guid(self):
        addon = self.node.get_addon(self.payload['provider'])
        path = self.payload['metadata']['path']
        path = path if path.startswith('/') else '/' + path
        self.guid, created = addon.find_or_create_file_guid(path)


class UpdateFileEvent(FileEvent):
    """
    Class for simple file operations such as updating, adding files
    """

    def __init__(self, user, node, event, payload=None):
        super(UpdateFileEvent, self).__init__(user, node, event, payload=payload)
        self.form_guid()
        self.form_event()
        self.form_message()
        self.form_url()

    def form_event(self):
        self.event = self.guid.guid_url.strip('/') + '_file_updated'

    def form_url(self):
        f_url = super(UpdateFileEvent, self).form_url()
        f_url.path = self.guid.guid_url
        self.url = f_url.url


class FileAdded(UpdateFileEvent):
    pass


class FileUpdated(UpdateFileEvent):
    pass


class SimpleFileEvent(FileEvent):
    """
    Class for file/folder operations that don't lead to a specific place
    """

    def __init__(self, user, node, event, payload=None):
        super(SimpleFileEvent, self).__init__(user, node, event, payload=payload)
        self.form_event()
        self.form_message()
        self.form_url()

    def form_url(self):
        """Forms a url that points at the file view"""
        f_url = super(SimpleFileEvent, self).form_url()
        f_url.path = self.node.web_url_for('collect_file_trees')
        self.url = f_url.url


class FileRemoved(SimpleFileEvent):
    pass


class FolderCreated(SimpleFileEvent):
    pass


class ComplexFileEvent(FileEvent):
    """
    Class for move and copy files. Users could be removed from subscription.
    """

    def __init__(self, user, node, event, payload=None):
        super(ComplexFileEvent, self).__init__(user, node, event, payload=payload)
        self.source_guid = None
        self.source_node = None
        self.form_guid()
        self.source_event_sub = None
        self.form_event()
        self.source_url = None
        self.form_url()
        self.form_message()

    def form_message(self):
        addon, f_type, action = tuple(self.action.split("_"))
        destination_name = self.payload['destination']['materialized'].strip('/')
        source_name = self.payload['source']['materialized'].strip('/')
        self.message = '{} "<b>{}</b>" from {} in {} to "<b>{}</b>" in {} in {}'.format(
            f_type, source_name, self.payload['source']['addon'], self.payload['source']['node']['title'],
            destination_name, self.payload['destination']['addon'], self.payload['destination']['node']['title']
        )

    def form_event(self):
        self.event = self.guid.guid_url.strip('/') + '_file_updated'
        self.source_event_sub = self.source_guid.guid_url.strip('/') + '_file_updated'

    def form_url(self):
        f_url = super(ComplexFileEvent, self).form_url()
        f_url.path = self.guid.guid_url
        self.url = f_url.url
        return f_url

    def form_guid(self):
        """Produces both guids"""
        addon = self.node.get_addon(self.payload['destination']['provider'])
        path = self.payload['destination']['path']
        path = path if path.startswith('/') else '/' + path
        self.guid, created = addon.find_or_create_file_guid(path)
        self.source_node = Node.load(self.payload['source']['node']['_id'])
        addon = self.source_node.get_addon(self.payload['source']['provider'])
        path = self.payload['source']['path']
        path = path if path.startswith('/') else '/' + path
        self.source_guid, created = addon.find_or_create_file_guid(path)


class AddonFileMoved(ComplexFileEvent):
    """
    Specific methods for handling moving files
    """
    def perform(self):
        rm_users = move_file_subscription(self.source_event_sub, self.source_node,
                                          self.event, self.node)
        message = self.message + ' Your subscription has been removed' \
                                 ' due to insufficient permissions in the new component.',
        warn_users_removed_from_subscription(rm_users, self.source_event_sub, self.user, self.source_node,
                                             timestamp=self.timestamp, gravatar_url=self.gravatar_url,
                                             message=message, url=self.source_url)
        super(AddonFileMoved, self).perform()

    def form_url(self):
        f_url = super(AddonFileMoved, self).form_url()
        f_url.path = self.node.web_url_for('collect_file_trees')
        self.source_url = f_url.url


class AddonFileCopied(ComplexFileEvent):
    """
    Specific methods for handling a copy file event.
    """
    def form_message(self):
        super(AddonFileCopied, self).form_message()
        self.message += ' You are not subscribed to the new file, follow link to add subscription.'

    def form_url(self):
        f_url = super(AddonFileCopied, self).form_url()
        f_url.path = self.source_guid.guid_url
        self.source_url = f_url.url
