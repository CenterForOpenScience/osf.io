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
        raise NotImplementedError

    @property
    def event(self):
        """String

        Examples:
            <waterbutler id>_file_updated"""
        raise NotImplementedError


class FileEvent(Event):

    """File event base class, should not be called directly"""
    def __init__(self, user, node, event, payload=None):
        super(FileEvent, self).__init__(user, node, event)
        self.payload = payload
        self._url = None

    @property
    def html_message(self):
        return '{action} {f_type} "<b>{name}</b>".'.format(
            action=tuple(self.action.split("_"))[1],
            f_type=tuple(self.action.split("_"))[0],
            name=self.payload['metadata']['materialized'].lstrip('/')
        )

    @property
    def text_message(self):
        return '{action} {f_type} "{name}".'.format(
            action=tuple(self.action.split("_"))[1],
            f_type=tuple(self.action.split("_"))[0],
            name=self.payload['metadata']['materialized'].lstrip('/')
        )

    @property
    def event(self):
        return "file_updated"

    @property
    def waterbutler_id(self):
        return self.payload['metadata']['path'].strip('/')

    @property
    def url(self):
        """Basis of making urls, this returns the url to the node."""
        if self._url is None:
            url = furl(self.node.absolute_url)
            url.path.segments = self.node.web_url_for(
                'collect_file_trees'
            ).split('/')

        return url


class FileAdded(FileEvent):
    """Actual class called when a file is added"""
    @property
    def event(self):
        return '{}_file_updated'.format(self.waterbutler_id)


class FileUpdated(FileEvent):
    """Actual class called when a file is updated"""
    @property
    def event(self):
        return '{}_file_updated'.format(self.waterbutler_id)


class FileRemoved(FileEvent):
    """Actual class called when a file is removed"""
    pass


class FolderCreated(FileEvent):
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

    @property
    def source_url(self):
        return self._source_url

    @property
    def html_message(self):
        # TODO: Factor these methods into a single, private method with a flag
        addon, f_type, action = tuple(self.action.split("_"))

        # TODO: see if this conditional is necessary
        if self.payload['destination']['kind'] == u'folder':
            f_type = 'folder'

        destination_name = self.payload['destination']['materialized'].lstrip('/')
        source_name = self.payload['source']['materialized'].lstrip('/')

        return (
            '{action} {f_type} "<b>{source_name}</b>" '
            'from {source_addon} in {source_node_title} '
            'to "<b>{dest_name}</b>" in {dest_addon} in {dest_node_title}.'
        ).format(
            action=action,
            f_type=f_type,
            source_name=source_name,
            source_addon=self.payload['source']['addon'],
            source_node_title=self.payload['source']['node']['title'],
            dest_name=destination_name,
            dest_addon=self.payload['destination']['addon'],
            dest_node_title=self.payload['destination']['node']['title'],
        )

    @property
    def text_message(self):
        addon, f_type, action = tuple(self.action.split("_"))

        # TODO: see if this conditional is necessary
        if self.payload['destination']['kind'] == u'folder':
            f_type = 'folder'

        destination_name = self.payload['destination']['materialized'].lstrip('/')
        source_name = self.payload['source']['materialized'].lstrip('/')

        return (
            '{action} {f_type} "<b>{source_name}</b>" '
            'from {source_addon} in {source_node_title} '
            'to "<b>{dest_name}</b>" in {dest_addon} in {dest_node_title}.'
        ).format(
            action=action,
            f_type=f_type,
            source_name=source_name,
            source_addon=self.payload['source']['addon'],
            source_node_title=self.payload['source']['node']['title'],
            dest_name=destination_name,
            dest_addon=self.payload['destination']['addon'],
            dest_node_title=self.payload['destination']['node']['title'],
        )

    @property
    def waterbutler_id(self):
        return self.payload['destination']['path'].strip('/')

    @property
    def event(self):
        """Sets event to be passed as well as the source event."""

        if self.payload['destination']['kind'] != u'folder':
            return '{}_file_updated'.format(self.waterbutler_id)  # folder

        return 'file_updated'  # file

    @property
    def source_url(self):
        url = furl(self.source_node.absolute_url)
        url.path.segments = self.source_node.web_url_for('collect_file_trees').split('/')

        return url


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

    @property
    def html_message(self):
        source = self.payload['source']['materialized'].rstrip('/').split('/')
        destination = self.payload['destination']['materialized'].rstrip('/').split('/')

        if source[:-1] == destination[:-1]:
            return 'renamed {} "<b>{}</b>" to "<b>{}</b>".'.format(
                    self.payload['destination']['kind'], self.payload['source']['materialized'],
                    self.payload['destination']['materialized']
                )

        return super(AddonFileMoved, self).html_message

    @property
    def text_message(self):
        source = self.payload['source']['materialized'].rstrip('/').split('/')
        destination = self.payload['destination']['materialized'].rstrip('/').split('/')

        if source[:-1] == destination[:-1]:
            return 'renamed {} "{}" to "{}".'.format(
                    self.payload['destination']['kind'], self.payload['source']['materialized'],
                    self.payload['destination']['materialized']
                )

        return super(AddonFileMoved, self).text_message


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

    @property
    def html_message(self):
        message = super(AddonFileCopied, self).html_message
        return message + ' You are not subscribed to the new file.'

    @property
    def text_message(self):
        message = super(AddonFileCopied, self).text_message
        return message + ' You are not subscribed to the new file.'
