"""
Event system + File events

- Provides a simple event registry (`event_registry`) and `@register` decorator.
- Defines the abstract `Event` base class.
- Implements file-related events and hooks them up to the addons file_updated signal.

If you relocate this file, make sure any imports pointing to
`notifications.events.base` are updated accordingly.
"""

from django.utils import timezone
from furl import furl
import markupsafe

from osf.models import (
    NotificationType,
    AbstractNode,
    NodeLog,
    Preprint,
)
from addons.base.signals import file_updated as signal


event_registry = {}


def register(event_type):
    """Register classes into event_registry."""
    def decorator(cls):
        event_registry[event_type] = cls
        return cls
    return decorator


class Event:
    """Base event class for notifications.

    Subclasses must implement:
      - text_message
      - html_message
      - url
      - event_type
    """
    def __init__(self, user, node, action):
        self.user = user
        self.profile_image_url = user.profile_image_url()
        self.node = node
        self.action = action
        self.timestamp = timezone.now()

    def perform(self):
        """Emit the notification through NotificationType."""
        NotificationType.objects.get(
            name=self.action
        ).emit(
            user=self.user,
            event_context={
                'user_fullname': self.user.fullname,
                'profile_image_url': self.profile_image_url,
                'action': self.action,
                'url': self.url,
                'message': self.html_message,
                'localized_timestamp': str(self.timestamp),
            }
        )

    @property
    def text_message(self):
        raise NotImplementedError

    @property
    def html_message(self):
        raise NotImplementedError

    @property
    def url(self):
        raise NotImplementedError

    @property
    def event_type(self):
        """Example: <waterbutler id>_file_updated"""
        raise NotImplementedError


# -----------------------------
# File events
# -----------------------------

@signal.connect
def file_updated(self, target=None, user=None, payload=None):
    """Signal receiver for addon file updates."""
    if isinstance(target, Preprint):
        return

    event = {
        'rename': NotificationType.Type.ADDON_FILE_RENAMED,
        'copy': NotificationType.Type.ADDON_FILE_COPIED,
        'create': NotificationType.Type.FILE_UPDATED,
        'move': NotificationType.Type.ADDON_FILE_MOVED,
        'delete': NotificationType.Type.FILE_REMOVED,
        'update': NotificationType.Type.FILE_UPDATED,
    }[payload.get('action')]

    if event not in event_registry:
        raise NotImplementedError(f'{event} not in {event_registry}')

    event_registry[event](user, target, event, payload=payload).perform()


class FileEvent(Event):
    """File event base class, should not be called directly."""

    def __init__(self, user, node, event, payload=None):
        super().__init__(user, node, event)
        self.payload = payload or {}
        self._url = None

    @property
    def html_message(self):
        f_type, action = self.action.split('_')
        print(self.payload)
        if self.payload['metadata']['path'].endswith('/'):
            f_type = 'folder'
        return '{action} {f_type} "<b>{name}</b>".'.format(
            action=markupsafe.escape(action),
            f_type=markupsafe.escape(f_type),
            name=markupsafe.escape(self.payload['metadata']['path'].lstrip('/'))
        )

    @property
    def text_message(self):
        f_type, action = self.action.split('_')
        if self.payload['metadata']['path'].endswith('/'):
            f_type = 'folder'
        return '{action} {f_type} "{name}".'.format(
            action=action,
            f_type=f_type,
            name=self.payload['metadata']['path'].lstrip('/')
        )

    @property
    def event_type(self):
        return 'file_updated'

    @property
    def waterbutler_id(self):
        return self.payload['metadata']['path'].strip('/')

    @property
    def url(self):
        # NOTE: furl encoding to be verified later
        if self._url is None:
            self._url = furl(
                self.node.absolute_url,
                path=self.node.web_url_for('collect_file_trees').split('/')
            )
        return self._url.url


@register(NodeLog.FILE_ADDED)
class FileAdded(FileEvent):
    @property
    def event_type(self):
        return f'{self.waterbutler_id}_file_updated'


@register(NodeLog.FILE_UPDATED)
class FileUpdated(FileEvent):
    @property
    def event_type(self):
        return f'{self.waterbutler_id}_file_updated'


@register(NodeLog.FILE_REMOVED)
class FileRemoved(FileEvent):
    pass


@register(NodeLog.FOLDER_CREATED)
class FolderCreated(FileEvent):
    pass


class ComplexFileEvent(FileEvent):
    """Parent class for move and copy files."""

    def __init__(self, user, node, event, payload=None):
        super().__init__(user, node, event, payload=payload)

        source_nid = self.payload['source']['node']['_id']
        self.source_node = AbstractNode.load(source_nid) or Preprint.load(source_nid)
        self.addon = self.node.get_addon(self.payload['destination']['provider'])

    def _build_message(self, html=False):
        addon, f_type, action = tuple(self.action.split('_'))
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
    def perform(self):
        # Same-node moves don’t need special perms messaging.
        if self.node == self.source_node:
            super().perform()
            return

        NotificationType.Type.ADDON_FILE_MOVED.instance.emit(
            user=self.user,
            event_context={
                'user_fullname': self.user.fullname,
                'message': self.html_message,
                'profile_image_url': self.profile_image_url,
                'localized_timestamp': self.timestamp,
                'url': self.url,
            },
            is_digest=True,
        )


@register(NodeLog.FILE_COPIED)
class AddonFileCopied(ComplexFileEvent):
    def perform(self):
        if self.node == self.source_node:
            super().perform()
            return

        NotificationType.Type.ADDON_FILE_MOVED.instance.emit(
            user=self.user,
            event_context={
                'user_fullname': self.user.fullname,
                'message': self.html_message,
                'profile_image_url': self.profile_image_url,
                'localized_timestamp': self.timestamp,
                'url': self.url,
            },
            is_digest=True,
        )
