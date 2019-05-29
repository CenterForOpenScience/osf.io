"""File event module

These classes are registered in event_registry and are callable through the
 register. The main way these are used is with the signals blinker module
 that catches the signal with the file_updated function.

FileEvent and ComplexFileEvent are parent classes with shared functionality.
"""
from furl import furl
import markupsafe

from website.notifications import emails
from website.notifications.constants import NOTIFICATION_TYPES
from website.notifications import utils
from website.notifications.events.base import (
    register, Event, event_registry, RegistryError
)
from website.notifications.events import utils as event_utils
from osf.models import AbstractNode, NodeLog, Preprint
from addons.base.signals import file_updated as signal


@signal.connect
def file_updated(self, target=None, user=None, event_type=None, payload=None):
    if isinstance(target, Preprint):
        return
    if event_type not in event_registry:
        raise RegistryError
    event = event_registry[event_type](user, target, event_type, payload=payload)
    event.perform()


class FileEvent(Event):
    """File event base class, should not be called directly"""

    def __init__(self, user, node, event, payload=None):
        super(FileEvent, self).__init__(user, node, event)
        self.payload = payload
        self._url = None

    @property
    def html_message(self):
        """Most basic html message"""
        f_type, action = self.action.split('_')
        if self.payload['metadata']['materialized'].endswith('/'):
            f_type = u'folder'
        return u'{action} {f_type} "<b>{name}</b>".'.format(
            action=markupsafe.escape(action),
            f_type=markupsafe.escape(f_type),
            name=markupsafe.escape(self.payload['metadata']['materialized'].lstrip('/'))
        )

    @property
    def text_message(self):
        """Most basic message without html tags. For future use."""
        f_type, action = self.action.split('_')
        if self.payload['metadata']['materialized'].endswith('/'):
            f_type = u'folder'
        return u'{action} {f_type} "{name}".'.format(
            action=action,
            f_type=f_type,
            name=self.payload['metadata']['materialized'].lstrip('/')
        )

    @property
    def event_type(self):
        """Most basic event type."""
        return 'file_updated'

    @property
    def waterbutler_id(self):
        """Waterbutler's file id for the file in question."""
        return self.payload['metadata']['path'].strip('/')

    @property
    def url(self):
        """Basis of making urls, this returns the url to the node."""
        if self._url is None:
            self._url = furl(self.node.absolute_url)
            self._url.path.segments = self.node.web_url_for(
                'collect_file_trees'
            ).split('/')

        return self._url.url


@register(NodeLog.FILE_ADDED)
class FileAdded(FileEvent):
    """Actual class called when a file is added"""

    @property
    def event_type(self):
        return u'{}_file_updated'.format(self.waterbutler_id)


@register(NodeLog.FILE_UPDATED)
class FileUpdated(FileEvent):
    """Actual class called when a file is updated"""

    @property
    def event_type(self):
        return u'{}_file_updated'.format(self.waterbutler_id)


@register(NodeLog.FILE_REMOVED)
class FileRemoved(FileEvent):
    """Actual class called when a file is removed"""
    pass


@register(NodeLog.FOLDER_CREATED)
class FolderCreated(FileEvent):
    """Actual class called when a folder is created"""
    pass


class ComplexFileEvent(FileEvent):
    """ Parent class for move and copy files."""
    def __init__(self, user, node, event, payload=None):
        super(ComplexFileEvent, self).__init__(user, node, event, payload=payload)

        source_nid = self.payload['source']['node']['_id']
        self.source_node = AbstractNode.load(source_nid) or Preprint.load(source_nid)
        self.addon = self.node.get_addon(self.payload['destination']['provider'])

    def _build_message(self, html=False):
        addon, f_type, action = tuple(self.action.split('_'))
        # f_type is always file for the action
        if self.payload['destination']['kind'] == u'folder':
            f_type = 'folder'

        destination_name = self.payload['destination']['materialized'].lstrip('/')
        source_name = self.payload['source']['materialized'].lstrip('/')

        if html:
            return (
                u'{action} {f_type} "<b>{source_name}</b>" '
                u'from {source_addon} in {source_node_title} '
                u'to "<b>{dest_name}</b>" in {dest_addon} in {dest_node_title}.'
            ).format(
                action=markupsafe.escape(action),
                f_type=markupsafe.escape(f_type),
                source_name=markupsafe.escape(source_name),
                source_addon=markupsafe.escape(self.payload['source']['addon']),
                source_node_title=markupsafe.escape(self.payload['source']['node']['title']),
                dest_name=markupsafe.escape(destination_name),
                dest_addon=markupsafe.escape(self.payload['destination']['addon']),
                dest_node_title=markupsafe.escape(self.payload['destination']['node']['title']),
            )
        return (
            u'{action} {f_type} "{source_name}" '
            u'from {source_addon} in {source_node_title} '
            u'to "{dest_name}" in {dest_addon} in {dest_node_title}.'
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
    def html_message(self):
        return self._build_message(html=True)

    @property
    def text_message(self):
        return self._build_message(html=False)

    @property
    def waterbutler_id(self):
        return self.payload['destination']['path'].strip('/')

    @property
    def event_type(self):
        if self.payload['destination']['kind'] != u'folder':
            return u'{}_file_updated'.format(self.waterbutler_id)  # file

        return u'file_updated'  # folder

    @property
    def source_url(self):
        url = furl(self.source_node.absolute_url)
        url.path.segments = self.source_node.web_url_for('collect_file_trees').split('/')

        return url.url


@register(NodeLog.FILE_RENAMED)
class AddonFileRenamed(ComplexFileEvent):
    """Actual class called when a file is renamed."""

    @property
    def html_message(self):
        return u'renamed {kind} "<b>{source_name}</b>" to "<b>{destination_name}</b>".'.format(
            kind=markupsafe.escape(self.payload['destination']['kind']),
            source_name=markupsafe.escape(self.payload['source']['materialized']),
            destination_name=markupsafe.escape(self.payload['destination']['materialized']),
        )

    @property
    def text_message(self):
        return u'renamed {kind} "{source_name}" to "{destination_name}".'.format(
            kind=self.payload['destination']['kind'],
            source_name=self.payload['source']['materialized'],
            destination_name=self.payload['destination']['materialized'],
        )


@register(NodeLog.FILE_MOVED)
class AddonFileMoved(ComplexFileEvent):
    """Actual class called when a file is moved."""

    def perform(self):
        """Format and send messages to different user groups.

        Users fall into three categories: moved, warned, and removed
        - Moved users are users with subscriptions on the new node.
        - Warned users are users without subscriptions on the new node, but
          they do have permissions
        - Removed users are told that they do not have permissions on the
          new node and their subscription has been removed.
        This will be **much** more useful when individual files have their
         own subscription.
        """
        # Do this is the two nodes are the same, no one needs to know specifics of permissions
        if self.node == self.source_node:
            super(AddonFileMoved, self).perform()
            return
        # File
        if self.payload['destination']['kind'] != u'folder':
            moved, warn, rm_users = event_utils.categorize_users(self.user, self.event_type, self.source_node,
                                                                 self.event_type, self.node)
            warn_message = u'{} You are no longer tracking that file based on the settings you selected for the component.'.format(self.html_message)
            remove_message = (u'{} Your subscription has been removed'
                              u' due to insufficient permissions in the new component.').format(self.html_message)
        # Folder
        else:
            # Gets all the files in a folder to look for permissions conflicts
            files = event_utils.get_file_subs_from_folder(self.addon, self.user, self.payload['destination']['kind'],
                                                          self.payload['destination']['path'],
                                                          self.payload['destination']['name'])
            # Bins users into different permissions
            moved, warn, rm_users = event_utils.compile_user_lists(files, self.user, self.source_node, self.node)

            # For users that don't have individual file subscription but has permission on the new node
            warn_message = u'{} You are no longer tracking that folder or files within based on the settings you selected for the component.'.format(self.html_message)
            # For users without permission on the new node
            remove_message = (u'{} Your subscription has been removed for the folder,'
                              u' or a file within,'
                              u' due to insufficient permissions in the new component.').format(self.html_message)

        # Move the document from one subscription to another because the old one isn't needed
        utils.move_subscription(rm_users, self.event_type, self.source_node, self.event_type, self.node)
        # Notify each user
        for notification in NOTIFICATION_TYPES:
            if notification == 'none':
                continue
            if moved[notification]:
                emails.store_emails(moved[notification], notification, 'file_updated', self.user, self.node,
                                    self.timestamp, message=self.html_message,
                                    profile_image_url=self.profile_image_url, url=self.url)
            if warn[notification]:
                emails.store_emails(warn[notification], notification, 'file_updated', self.user, self.node,
                                    self.timestamp, message=warn_message, profile_image_url=self.profile_image_url,
                                    url=self.url)
            if rm_users[notification]:
                emails.store_emails(rm_users[notification], notification, 'file_updated', self.user, self.source_node,
                                    self.timestamp, message=remove_message,
                                    profile_image_url=self.profile_image_url, url=self.source_url)


@register(NodeLog.FILE_COPIED)
class AddonFileCopied(ComplexFileEvent):
    """Actual class called when a file is copied"""
    def perform(self):
        """Format and send messages to different user groups.

        This is similar to the FileMoved perform method. The main
         difference is the moved and earned user groups are added
         together because they both don't have a subscription to a
         newly copied file.
        """
        remove_message = self.html_message + ' You do not have permission in the new component.'
        if self.node == self.source_node:
            super(AddonFileCopied, self).perform()
            return
        if self.payload['destination']['kind'] != u'folder':
            moved, warn, rm_users = event_utils.categorize_users(self.user, self.event_type, self.source_node,
                                                                 self.event_type, self.node)
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
                                    message=self.html_message, profile_image_url=self.profile_image_url, url=self.url)
            if rm_users[notification]:
                emails.store_emails(rm_users[notification], notification, 'file_updated', self.user, self.source_node,
                                    self.timestamp, message=remove_message,
                                    profile_image_url=self.profile_image_url, url=self.source_url)
