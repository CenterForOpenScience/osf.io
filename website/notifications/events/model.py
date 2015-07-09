# -*- coding: utf-8 -*-
"""Basic Event handling for events that need subscriptions"""

from furl import furl
from datetime import datetime
from six import add_metaclass

import website.notifications.emails as emails
from website.notifications.constants import NOTIFICATION_TYPES
from website.models import Node
from website.notifications.events import utils


class _EventMeta(type):
    registry = {}

    def __init__(cls, name, bases, attrs):
        if name != 'Event':
            event_id = name.lower()
            cls.registry[event_id] = cls

        super(_EventMeta, cls).__init__(name, bases, attrs)


@add_metaclass(_EventMeta)
class Event(object):
    """
    Base notification class for building notification events and messages.
    - abstract methods set methods that must be defined by subclasses.

    To use this interface you must use the class as a Super (inherited).
     - Implement the form_ methods in the subclass
     - All subclasses must be in this file for the meta class to list them
     - Name the subclasses you will be calling as such:
      - event (the type of event from _SUBSCRIPTIONS_AVAILABLE or specific cases)
      - class
      example: event = file_added, class = FileAdded
    """
    _text_message = None
    _html_message = None
    _url = None
    _event = None

    def __init__(self, user, node, action):
        self.user = user
        self.gravatar_url = user.gravatar_url
        self.node = node
        self.node_id = node._id
        self.action = action
        self.timestamp = datetime.utcnow()

    @classmethod
    def parse_event(cls, user, node, event, **kwargs):
        """If there is a class that matches the event then it returns that instance"""
        kind = ''.join(event.split('_'))
        if kind in cls.registry:
            return cls.registry[kind](user, node, event, **kwargs)
        raise TypeError

    def perform(self):
        """Calls emails.notify"""
        emails.notify(
            uid=self.node_id,
            event=self.event,
            user=self.user,
            node=self.node,
            timestamp=self.timestamp,
            message=self.html_message,
            gravatar_url=self.gravatar_url,
            url=self.url
        )

    @property
    def text_message(self):
        return self._text_message

    @property
    def html_message(self):
        return self._html_message

    @property
    def url(self):
        return self._url

    @property
    def event(self):
        return self._event

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
    _guid = None

    """File event base class, should not be called directly"""
    def __init__(self, user, node, event, payload=None):
        super(FileEvent, self).__init__(user, node, event)
        self.payload = payload
        self._guid = None

    @property
    def guid(self):
        return self._guid

    def form_message(self):
        """Sets the message to 'action file/folder <location>' """
        f_type, action = tuple(self.action.split("_"))
        name = self.payload['metadata']['materialized'].lstrip('/')
        self._html_message = '{} {} "<b>{}</b>".'.format(action, f_type, name)
        self._text_message = '{} {} "{}".'.format(action, f_type, name)

    def form_event(self):
        """Simplest event set"""
        self._event = "file_updated"

    def form_url(self):
        """Basis of making urls, this returns the url to the node."""
        f_url = furl(self.node.absolute_url)
        return f_url

    def form_guid(self):
        """Gets the UID for the file to use with self.event and self.url"""
        addon = self.node.get_addon(self.payload['provider'])
        path = self.payload['metadata']['path']
        path = path if path.startswith('/') else '/' + path
        self._guid, created = addon.find_or_create_file_guid(path)


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
        """Add guid to file_updated"""
        self._event = self.guid.guid_url.strip('/') + '_file_updated'

    def form_url(self):
        """Build url to file view"""
        f_url = super(UpdateFileEvent, self).form_url()
        f_url.path = self.guid.guid_url
        self._url = f_url.url


class FileAdded(UpdateFileEvent):
    """Actual class called when a file is added"""
    pass


class FileUpdated(UpdateFileEvent):
    """Actual class called when a file is updated"""
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
        """Forms a url that points at the files view, not the folder or deleted file."""
        f_url = super(SimpleFileEvent, self).form_url()
        f_url.path = self.node.web_url_for('collect_file_trees')
        self._url = f_url.url


class FileRemoved(SimpleFileEvent):
    """Actual class called when a file is removed"""
    pass


class FolderCreated(SimpleFileEvent):
    """Actual class called when a folder is created"""
    pass


class ComplexFileEvent(FileEvent):
    """
    Class for move and copy files. Users could be removed from subscription.
    - Essentially every method is redone for these more complex actions.
    """
    _source_guid = None
    _source_event = None
    _source_url = None

    def __init__(self, user, node, event, payload=None):
        super(ComplexFileEvent, self).__init__(user, node, event, payload=payload)
        self.source_node = None
        self.addon = None
        self.form_guid()
        self.form_event()
        self.form_url()
        self.form_message()

    @property
    def source_guid(self):
        return self._source_guid

    @property
    def source_event(self):
        return self._source_event

    @property
    def source_url(self):
        return self._source_url

    def form_message(self):
        """lists source and destination in message"""
        addon, f_type, action = tuple(self.action.split("_"))
        if self.payload['destination']['kind'] == u'folder':
            f_type = 'folder'
        destination_name = self.payload['destination']['materialized'].lstrip('/')
        source_name = self.payload['source']['materialized'].lstrip('/')
        self._html_message = '{} {} "<b>{}</b>" from {} in {} to "<b>{}</b>" in {} in {}.'.format(
            action, f_type, source_name, self.payload['source']['addon'], self.payload['source']['node']['title'],
            destination_name, self.payload['destination']['addon'], self.payload['destination']['node']['title']
        )
        self._text_message = '{} {} "{}" from {} in {} to "{}" in {} in {}.'.format(
            action, f_type, source_name, self.payload['source']['addon'], self.payload['source']['node']['title'],
            destination_name, self.payload['destination']['addon'], self.payload['destination']['node']['title']
        )

    def form_event(self):
        """Sets event to be passed as well as the source event."""
        if self.payload['destination']['kind'] != u'folder':
            self._event = self.guid.guid_url.strip('/') + '_file_updated'
            self._source_event = self.source_guid.guid_url.strip('/') + '_file_updated'
        else:
            self._event = 'file_updated'
            self._source_event = 'file_updated'

    def form_url(self):
        f_url = super(ComplexFileEvent, self).form_url()
        if self.payload['destination']['kind'] == u'folder':
            f_url.path = self.node.web_url_for('collect_file_trees')
        else:
            f_url.path = self.guid.guid_url
        self._url = f_url.url
        return f_url

    def form_guid(self):
        """Produces both guids for source and destination"""
        # if self.payload['destination']['kind'] != u'folder':
        self.addon = self.node.get_addon(self.payload['destination']['provider'])
        self._guid = utils.get_file_guid(self.node, self.payload['destination']['provider'],
                                         self.payload['destination']['path'])
        self.source_node = Node.load(self.payload['source']['node']['_id'])
        self._source_guid = utils.get_file_guid(self.source_node, self.payload['source']['provider'],
                                                self.payload['destination']['path'])


class AddonFileMoved(ComplexFileEvent):
    """
    Actual class called when a file is moved
    Specific methods for handling moving files
    """
    def perform(self):
        """Sends a message to users who are removed from the file's subscription when it is moved"""
        if self.node == self.source_node:
            super(AddonFileMoved, self).perform()
            return
        if self.payload['destination']['kind'] != u'folder':
            moved, warn, rm_users = utils.categorize_users(self.user, self.source_event, self.source_node,
                                                           self.event, self.node)
            warn_message = self.html_message + ' Your component-level subscription was not transferred.'
            remove_message = self.html_message + ' Your subscription has been removed' \
                                                 ' due to insufficient permissions in the new component.'
        else:
            files = utils.get_file_subs_from_folder(self.addon, self.user, self.payload['destination']['kind'],
                                                    self.payload['destination']['path'],
                                                    self.payload['destination']['name'])
            moved, warn, rm_users = self.compile_user_lists(files)
            warn_message = self.html_message + ' Your component-level subscription was not transferred.'
            remove_message = self.html_message + ' Your subscription has been removed for the folder or a file within' \
                                                 ' due to insufficient permissions in the new component.'
        for notification in NOTIFICATION_TYPES:
            if notification == 'none':
                continue
            if moved[notification]:
                emails.send(moved[notification], notification, self.node_id, 'file_updated', self.user, self.node,
                            self.timestamp, message=self.html_message, gravatar_url=self.gravatar_url,
                            url=self.url)
            if warn[notification]:
                emails.send(warn[notification], notification, self.node_id, 'file_updated', self.user, self.node,
                            self.timestamp, message=warn_message, gravatar_url=self.gravatar_url,
                            url=self.url)
            if rm_users[notification]:
                emails.send(rm_users[notification], notification, self.node_id, 'file_updated', self.user,
                            self.source_node, self.timestamp, message=remove_message,
                            gravatar_url=self.gravatar_url, url=self.source_url)

    def compile_user_lists(self, files):
        move = {key: [] for key in NOTIFICATION_TYPES}
        warn = {key: [] for key in NOTIFICATION_TYPES}
        remove = {key: [] for key in NOTIFICATION_TYPES}
        for file_path in files:
            guid = utils.get_file_guid(self.node, self.payload['destination']['provider'], file_path)
            source_guid = utils.get_file_guid(self.source_node, self.payload['source']['provider'], file_path)
            t_move, t_warn, t_remove = \
                utils.categorize_users(self.user, source_guid.guid_url.strip('/') + '_file_updated', self.source_node,
                                       guid.guid_url.strip('/') + '_file_updated', self.node)
            for notification in NOTIFICATION_TYPES:
                move[notification] = list(set(move[notification]).union(set(t_move[notification])))
                warn[notification] = list(set(warn[notification]).union(set(t_warn[notification])))
                remove[notification] = list(set(remove[notification]).union(set(t_remove[notification])))
        return move, warn, remove

    def form_url(self):
        """Set source url for subscribers removed from subscription to files page view"""
        f_url = super(AddonFileMoved, self).form_url()
        f_url.path = self.node.web_url_for('collect_file_trees')
        self._source_url = f_url.url


class AddonFileCopied(ComplexFileEvent):
    """
    Actual class called when a file is copied
    Specific methods for handling a copy file event.
    """
    def form_message(self):
        """Adds warning to message to tell user that subscription did not copy with the file."""
        super(AddonFileCopied, self).form_message()
        self._html_message += ' You are not subscribed to the new file, follow link to add subscription.'
        self._text_message += ' You are not subscribed to the new file, follow link to add subscription.'

    # TODO: Actually use this once the path from WB comes back properly
    def form_url(self):
        """Source url points to original file"""
        f_url = super(AddonFileCopied, self).form_url()
        # if self.payload['destination']['kind'] != u'folder':
        #     f_url.path = self.source_guid.guid_url
        # else:
        #     f_url.path = self.source_node.web_url_for('collect_file_tree')
        # self._source_url = f_url.url
