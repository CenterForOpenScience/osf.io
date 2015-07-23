# -*- coding: utf-8 -*-
"""Basic Event handling for events that need subscriptions"""

from furl import furl
from datetime import datetime
from six import add_metaclass

from website.notifications import emails
from website.notifications.constants import NOTIFICATION_TYPES
from website.models import Node
from website.notifications.events import utils as event_utils
from website.notifications import utils


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
        """Calls emails.notify to notify users of an action"""
        emails.notify(
            event=self.event,
            user=self.user,
            node=self.node,
            timestamp=self.timestamp,
            message=self.html_message,
            gravatar_url=self.gravatar_url,
            url=self.url.url
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
    _wbid = None  # waterbutler id/path

    """File event base class, should not be called directly"""
    def __init__(self, user, node, event, payload=None):
        super(FileEvent, self).__init__(user, node, event)
        self.payload = payload
        self._wbid = None

    @property
    def wbid(self):
        return self._wbid

    def form_message(self):
        """Sets the message to 'action file/folder <location>' """
        f_type, action = tuple(self.action.split("_"))
        name = self.payload['metadata']['materialized'].lstrip('/')
        self._html_message = '{} {} "<b>{}</b>".'.format(action, f_type, name)
        self._text_message = '{} {} "{}".'.format(action, f_type, name)

    def form_event(self):
        """Simplest event set"""
        self._event = "file_updated"
        self._wbid = self.payload['metadata']['path'].strip('/')

    def form_url(self):
        """Basis of making urls, this returns the url to the node."""
        self._url = furl(self.node.absolute_url)
        self._url.path.segments = self.node.web_url_for('collect_file_trees').split('/')


class UpdateFileEvent(FileEvent):
    """
    Class for simple file operations such as updating, adding files
    """
    def __init__(self, user, node, event, payload=None):
        super(UpdateFileEvent, self).__init__(user, node, event, payload=payload)
        self.form_event()
        self.form_message()
        self.form_url()

    def form_event(self):
        """Add waterbutler id to file_updated"""
        super(UpdateFileEvent, self).form_event()
        self._event = self.wbid + '_file_updated'


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
    _source_url = None

    def __init__(self, user, node, event, payload=None):
        super(ComplexFileEvent, self).__init__(user, node, event, payload=payload)
        self.source_node = Node.load(self.payload['source']['node']['_id'])
        self.addon = self.node.get_addon(self.payload['destination']['provider'])
        self.form_event()
        self.form_url()
        self.form_message()

    @property
    def source_wbid(self):
        return self._source_wbid

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
        self._wbid = self.payload['destination']['path'].strip('/')
        if self.payload['destination']['kind'] != u'folder':
            self._event = self.wbid + '_file_updated'
        else:
            self._event = 'file_updated'

    def form_url(self):
        super(ComplexFileEvent, self).form_url()
        self._source_url = furl(self.source_node.absolute_url)
        self._source_url.path.segments = self.source_node.web_url_for('collect_file_trees').split('/')


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
            moved, warn, rm_users = event_utils.categorize_users(self.user, self.event, self.source_node,
                                                                 self.event, self.node)
            warn_message = self.html_message + ' Your component-level subscription was not transferred.'
            remove_message = self.html_message + ' Your subscription has been removed' \
                                                 ' due to insufficient permissions in the new component.'
        else:
            files = event_utils.get_file_subs_from_folder(self.addon, self.user, self.payload['destination']['kind'],
                                                          self.payload['destination']['path'],
                                                          self.payload['destination']['name'])
            moved, warn, rm_users = event_utils.compile_user_lists(files, self.user, self.source_node, self.node)
            warn_message = self.html_message + ' Your component-level subscription was not transferred.'
            remove_message = self.html_message + ' Your subscription has been removed for the folder,' \
                                                 ' or a file within,' \
                                                 ' due to insufficient permissions in the new component.'

        utils.move_subscription(rm_users, self.event, self.source_node, self.event, self.node)
        for notification in NOTIFICATION_TYPES:
            if notification == 'none':
                continue
            if moved[notification]:
                emails.store_emails(moved[notification], notification, 'file_updated', self.user, self.node,
                                    self.timestamp, message=self.html_message,
                                    gravatar_url=self.gravatar_url, url=self.url.url)
            if warn[notification]:
                emails.store_emails(warn[notification], notification, 'file_updated', self.user, self.node,
                                    self.timestamp, message=warn_message, gravatar_url=self.gravatar_url,
                                    url=self.url.url)
            if rm_users[notification]:
                emails.store_emails(rm_users[notification], notification, 'file_updated', self.user, self.source_node,
                                    self.timestamp, message=remove_message,
                                    gravatar_url=self.gravatar_url, url=self.source_url.url)


class AddonFileCopied(ComplexFileEvent):
    """
    Actual class called when a file is copied
    Specific methods for handling a copy file event.
    """
    def perform(self):
        """Warns people that they won't have a subscription to the new copy of the file."""
        remove_message = self.html_message + ' This is due to insufficient permissions in the new component.'
        if self.node == self.source_node:
            super(AddonFileCopied, self).perform()
            return
        if self.payload['destination']['kind'] != u'folder':
            moved, warn, rm_users = event_utils.categorize_users(self.user, self.event, self.source_node,
                                                                 self.event, self.node)
        else:
            files = event_utils.get_file_subs_from_folder(self.addon, self.user, self.payload['destination']['kind'],
                                                          self.payload['destination']['path'],
                                                          self.payload['destination']['name'])
            moved, warn, rm_users = event_utils.compile_user_lists(files, self.user, self.source_node, self.node)
        for notification in NOTIFICATION_TYPES:
            if notification == 'none':
                continue
            if moved[notification] or warn[notification]:
                users = list(set(moved[notification]).union(set(warn[notification])))
                emails.store_emails(users, notification, 'file_updated', self.user, self.node, self.timestamp,
                                    message=self.html_message, gravatar_url=self.gravatar_url, url=self.url.url)
            if rm_users[notification]:
                emails.store_emails(rm_users[notification], notification, 'file_updated', self.user, self.source_node,
                                    self.timestamp, message=remove_message,
                                    gravatar_url=self.gravatar_url, url=self.source_url.url)

    def form_message(self):
        """Adds warning to message to tell user that subscription did not copy with the file."""
        super(AddonFileCopied, self).form_message()
        self._html_message += ' You are not subscribed to the new file.'
        self._text_message += ' You are not subscribed to the new file.'

    def form_url(self):
        """Source url points to original file"""
        super(AddonFileCopied, self).form_url()
