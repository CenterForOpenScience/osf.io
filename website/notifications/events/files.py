"""File event module

These classes are registered in event_registry and are callable through the
 register. The main way these are used is with the signals blinker module
 that catches the signal with the file_updated function.

FileEvent and ComplexFileEvent are parent classes with shared functionality.
"""
from django.utils import timezone
from furl import furl
import markupsafe

from website.notifications.events.base import (
    register,
    event_registry,
    RegistryError,
)
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


class FileEvent:
    """File event base class, should not be called directly"""

    """Base event class for notification.

    - abstract methods set methods that should be defined by subclasses.
    To use this interface you must use the class as a Super (inherited).
     - Implement property methods in subclasses
    """

    def __init__(self, user, node, action, payload=None):
        self.user = user
        self.profile_image_url = user.profile_image_url()
        self.node = node
        self.action = action
        self.timestamp = timezone.now()
        self.payload = payload
        self._url = None

    def perform(self):
        """Call emails.notify to notify users of an action"""
        from osf.models import NotificationType, NotificationSubscription
        from django.contrib.contenttypes.models import ContentType

        subscription, _ = NotificationSubscription.objects.get_or_create(
            user=self.user,
            notification_type=NotificationType.objects.get(name=self.action),
            content_type=ContentType.objects.get_for_model(self.node.__class__),
            object_id=self.node.id,
        )
        subscription.emit(
            user=self.user,
            subscribed_object=self.node,
            event_context=self.payload,

        )

    @property
    def html_message(self):
        """Most basic html message"""
        f_type, action = self.action.split('_')
        if self.payload['metadata']['materialized'].endswith('/'):
            f_type = 'folder'
        return '{action} {f_type} "<b>{name}</b>".'.format(
            action=markupsafe.escape(action),
            f_type=markupsafe.escape(f_type),
            name=markupsafe.escape(self.payload['metadata']['materialized'].lstrip('/'))
        )

    @property
    def text_message(self):
        """Most basic message without html tags. For future use."""
        f_type, action = self.action.split('_')
        if self.payload['metadata']['materialized'].endswith('/'):
            f_type = 'folder'
        return '{action} {f_type} "{name}".'.format(
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
            # NOTE: furl encoding to be verified later
            self._url = furl(
                self.node.absolute_url,
                path=self.node.web_url_for('collect_file_trees').split('/')
            )

        return self._url.url


@register(NodeLog.FILE_ADDED)
class FileAdded(FileEvent):
    """Actual class called when a file is added"""

@register(NodeLog.FILE_UPDATED)
class FileUpdated(FileEvent):
    """Actual class called when a file is updated"""

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
        super().__init__(user, node, event, payload=payload)

        source_nid = self.payload['source']['node']['_id']
        self.source_node = AbstractNode.load(source_nid) or Preprint.load(source_nid)
        self.addon = self.node.get_addon(self.payload['destination']['provider'])

    def _build_message(self, html=False):
        addon, f_type, action = tuple(self.action.split('_'))
        # f_type is always file for the action
        if self.payload['destination']['kind'] == 'folder':
            f_type = 'folder'

        destination_name = self.payload['destination']['materialized'].lstrip('/')
        source_name = self.payload['source']['materialized'].lstrip('/')

        if html:
            return (
                '{action} {f_type} "<b>{source_name}</b>" '
                'from {source_addon} in {source_node_title} '
                'to "<b>{dest_name}</b>" in {dest_addon} in {dest_node_title}.'
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
            '{action} {f_type} "{source_name}" '
            'from {source_addon} in {source_node_title} '
            'to "{dest_name}" in {dest_addon} in {dest_node_title}.'
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
        if self.payload['destination']['kind'] != 'folder':
            return f'{self.waterbutler_id}_file_updated'  # file

        return 'file_updated'  # folder

    @property
    def source_url(self):
        # NOTE: furl encoding to be verified later
        url = furl(
            self.source_node.absolute_url,
            path=self.source_node.web_url_for('collect_file_trees').split('/')
        )
        return url.url


@register(NodeLog.FILE_RENAMED)
class AddonFileRenamed(ComplexFileEvent):
    """Actual class called when a file is renamed."""

    @property
    def html_message(self):
        return 'renamed {kind} "<b>{source_name}</b>" to "<b>{destination_name}</b>".'.format(
            kind=markupsafe.escape(self.payload['destination']['kind']),
            source_name=markupsafe.escape(self.payload['source']['materialized']),
            destination_name=markupsafe.escape(self.payload['destination']['materialized']),
        )

    @property
    def text_message(self):
        return 'renamed {kind} "{source_name}" to "{destination_name}".'.format(
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
        pass
        # Do this is the two nodes are the same, no one needs to know specifics of permissions
        if self.node == self.source_node:
            super().perform()
            return
        # # File
        # if self.payload['destination']['kind'] != 'folder':
        #     moved, warn, rm_users = None, None, None
        #     warn_message = f'{self.html_message} You are no longer tracking that file based on the settings you selected for the component.'
        #     remove_message = (
        #         f'{self.html_message} Your subscription has been removed due to '
        #         'insufficient permissions in the new component.'
        #     )
        # # Folder
        # else:
        #     # Gets all the files in a folder to look for permissions conflicts
        #     files = None
        #     # Bins users into different permissions
        #     moved, warn, rm_users = None, None, None
        #
        #     # For users that don't have individual file subscription but has permission on the new node
        #     warn_message = f'{self.html_message} You are no longer tracking that folder or files within based on the settings you selected for the component.'
        #     # For users without permission on the new node
        #     remove_message = (
        #         f'{self.html_message} Your subscription has been removed for the '
        #         'folder, or a file within, due to insufficient permissions in the new '
        #         'component.'
        #     )
        #
        # # Notify each user
        # NOTIFICATION_TYPES = {
        #     'none': 'none',
        #     'instant': 'email_transactional',
        #     'daily': 'email_digest',
        # }
        # for notification in NOTIFICATION_TYPES:
        #     if notification == 'none':
        #         continue
        #     if moved[notification]:
        #         emails.store_emails(moved[notification], notification, 'file_updated', self.user, self.node,
        #                             self.timestamp, message=self.html_message,
        #                             profile_image_url=self.profile_image_url, url=self.url)
        #     if warn[notification]:
        #         emails.store_emails(warn[notification], notification, 'file_updated', self.user, self.node,
        #                             self.timestamp, message=warn_message, profile_image_url=self.profile_image_url,
        #                             url=self.url)
        #     if rm_users[notification]:
        #         emails.store_emails(rm_users[notification], notification, 'file_updated', self.user, self.source_node,
        #                             self.timestamp, message=remove_message,
        #                             profile_image_url=self.profile_image_url, url=self.source_url)


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
        pass
