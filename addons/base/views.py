import datetime
import os
import uuid
import markupsafe
from urllib.parse import quote
from django.utils import timezone

from flask import make_response
from flask import request
from furl import furl
import jwe
import jwt
from osf.external.gravy_valet.translations import EphemeralNodeSettings
import waffle
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from elasticsearch import exceptions as es_exceptions
from rest_framework import status as http_status

from api.caching.tasks import update_storage_usage_with_size

from addons.base import exceptions as addon_errors
from addons.base.models import BaseStorageAddon
from addons.osfstorage.models import OsfStorageFileNode
from addons.osfstorage.utils import enqueue_update_analytics

from api.waffle.utils import flag_is_active
from framework import sentry
from framework.auth import Auth
from framework.auth import cas
from framework.auth import oauth_scopes
from framework.auth.decorators import collect_auth, must_be_logged_in, must_be_signed
from framework.exceptions import HTTPError
from framework.flask import redirect
from framework.sentry import log_exception
from framework.transactions.handlers import no_auto_transaction
from website import settings
from addons.base import signals as file_signals
from addons.base.utils import format_last_known_metadata, get_mfr_url
from osf import features
from osf.models import (
    BaseFileNode,
    TrashedFileNode,
    BaseFileVersionsThrough,
    OSFUser,
    AbstractNode,
    Preprint,
    Node,
    NodeLog,
    Registration,
    DraftRegistration,
    Guid,
    FileVersionUserMetadata,
    FileVersion, NotificationType
)
from osf.metrics import PreprintView, PreprintDownload
from osf.utils import permissions
from osf.external.gravy_valet import request_helpers
from website.profile.utils import get_profile_image_url
from website.project import decorators
from website.project.decorators import must_be_contributor_or_public, must_be_valid_project, check_contributor_auth
from website.project.utils import serialize_node
from website.util import rubeus

# import so that associated listener is instantiated and gets emails
from notifications.file_event_notifications import FileEvent  # noqa

ERROR_MESSAGES = {'FILE_GONE': """
<style>
#toggleBar{{display: none;}}
</style>
<div class="alert alert-info" role="alert">
<p>
The file "{file_name}" stored on {provider} was deleted via the OSF.
</p>
<p>
It was deleted by <a href="/{deleted_by_guid}">{deleted_by}</a> on {deleted_on}.
</p>""",
                  'FILE_GONE_ACTOR_UNKNOWN': """
<style>
#toggleBar{{display: none;}}
</style>
<div class="alert alert-info" role="alert">
<p>
The file "{file_name}" stored on {provider} was deleted via the OSF.
</p>
<p>
It was deleted on {deleted_on}.
</p>""",
                  'DONT_KNOW': """
<style>
#toggleBar{{display: none;}}
</style>
<div class="alert alert-info" role="alert">
<p>
File not found at {provider}.
</p>""",
                  'BLAME_PROVIDER': """
<style>
#toggleBar{{display: none;}}
</style>
<div class="alert alert-info" role="alert">
<p>
This {provider} link to the file "{file_name}" is currently unresponsive.
The provider ({provider}) may currently be unavailable or "{file_name}" may have been removed from {provider} through another interface.
</p>
<p>
You may wish to verify this through {provider}'s website.
</p>""",
                  'FILE_SUSPENDED': """
<style>
#toggleBar{{display: none;}}
</style>
<div class="alert alert-info" role="alert">
This content has been removed."""}

WATERBUTLER_JWE_KEY = jwe.kdf(settings.WATERBUTLER_JWE_SECRET.encode('utf-8'), settings.WATERBUTLER_JWE_SALT.encode('utf-8'))

_READ_ACTIONS = frozenset([
    'revisions',
    'metadata',
    'download',
    'render',
    'export',
    'copyfrom',
])
_WRITE_ACTIONS = frozenset([
    'create_folder',
    'upload',
    'delete',
    'copy',
    'move',
    'copyto',
    'moveto',
    'movefrom',
])


@decorators.must_have_permission(permissions.WRITE)
@decorators.must_not_be_registration
def disable_addon(auth, **kwargs):
    node = kwargs['node'] or kwargs['project']

    addon_name = kwargs.get('addon')
    if addon_name is None:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    deleted = node.delete_addon(addon_name, auth)

    return {'deleted': deleted}


@must_be_logged_in
def get_addon_user_config(**kwargs):

    user = kwargs['auth'].user

    addon_name = kwargs.get('addon')
    if addon_name is None:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    addon = user.get_addon(addon_name)
    if addon is None:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    return addon.to_json(user)


def _download_is_from_mfr(waterbutler_data):
    metrics_data = waterbutler_data.get('metrics', {})
    uri = metrics_data.get('uri', '')
    is_render_uri = furl(uri).query.params.get('mode') == 'render'
    return (
        # This header is sent for download requests that
        # originate from MFR, e.g. for the code pygments renderer
        request.headers.get('X-Cos-Mfr-Render-Request', None) or
        # Need to check the URI in order to account
        # for renderers that send XHRs from the
        # rendered content, e.g. PDFs
        is_render_uri
    )


def make_auth(user):
    if user is not None:
        return {
            'id': user._id,
            'email': f'{user._id}@osf.io',
            'name': user.fullname,
        }
    return {}


@collect_auth
def get_auth(auth, **kwargs):
    """
    Authenticate a request and construct a JWT payload for Waterbutler callbacks.
    When a user interacts with a file OSF sends a request to WB which itself sends a
    request to an external service or Osfstorage, in order to confirm that event has
    taken place Waterbutler will send this callback to OSF to comfirm the file action was
    successful and can be logged.

    This function decrypts and decodes the JWT payload from the request, authenticates
    the resource based on the node ID provided in the JWT payload, and ensures the user
    has the required permissions to perform the specified action on the node. If the user
    is not authenticated, it attempts to authenticate them using the provided data. This
    function also constructs a response payload that includes a signed and encrypted JWT,
    which Waterbutler can use to verify the request.

    Parameters:
        auth (Auth): The authentication context, typically collected by the `@collect_auth` decorator.
        **kwargs: Keyword arguments that might include additional context needed for complex permissions checks.

    Returns:
        dict: A dictionary containing the encrypted JWT in 'payload', ready to be used by Waterbutler.

    Raises:
        HTTPError: If authentication fails, the node does not exist, the action is not allowed, or
                   any required data for authentication is missing from the request.
    """
    waterbutler_data = _decrypt_and_decode_jwt_payload()
    resource = _get_authenticated_resource(waterbutler_data['nid'])

    action = waterbutler_data['action']
    _check_resource_permissions(resource, auth, action)

    provider_name = waterbutler_data['provider']
    waterbutler_settings = None
    waterbutler_credentials = None
    file_version = file_node = None
    if provider_name == 'osfstorage' or (not flag_is_active(request, features.ENABLE_GV)):
        file_version, file_node = _get_osfstorage_file_version_and_node(
            file_path=waterbutler_data.get('path'), file_version_id=waterbutler_data.get('version')
        )
        waterbutler_settings, waterbutler_credentials = _get_waterbutler_configs(
            resource=resource, provider_name=provider_name, file_version=file_version,
        )
    else:
        result = request_helpers.get_waterbutler_config(
            gv_addon_pk=f'{waterbutler_data['nid']}:{waterbutler_data['provider']}',
            requested_resource=resource,
            requesting_user=auth.user,
            addon_type='configured-storage-addons',
        )
        if not result:
            raise HTTPError(http_status.HTTP_404_NOT_FOUND, 'Requested Provider is not configured for given node')
        waterbutler_settings = result.get_attribute('config')
        waterbutler_credentials = result.get_attribute('credentials')

    _enqueue_metrics(
        file_version=file_version,
        file_node=file_node,
        action=action,
        auth=auth,
        from_mfr=_download_is_from_mfr(waterbutler_data),
    )

    # Construct the response payload including the JWT
    return _construct_payload(
        auth=auth,
        resource=resource,
        credentials=waterbutler_credentials,
        waterbutler_settings=waterbutler_settings
    )


def _decrypt_and_decode_jwt_payload():
    try:
        payload_encrypted = request.args.get('payload', '').encode('utf-8')
        payload_decrypted = jwe.decrypt(payload_encrypted, WATERBUTLER_JWE_KEY)
        return jwt.decode(
            payload_decrypted,
            settings.WATERBUTLER_JWT_SECRET,
            options={'require_exp': True},
            algorithms=[settings.WATERBUTLER_JWT_ALGORITHM]
        )['data']
    except (jwt.InvalidTokenError, KeyError) as err:
        sentry.log_message(str(err))
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)


def _get_authenticated_resource(resource_id):
    resource, _ = Guid.load_referent(resource_id)

    if not resource:
        raise HTTPError(http_status.HTTP_404_NOT_FOUND, message='Resource not found.')

    if resource.deleted:
        raise HTTPError(http_status.HTTP_410_GONE, message='Resource has been deleted.')

    if getattr(resource, 'is_retracted', False):
        raise HTTPError(http_status.HTTP_410_GONE, message='Resource has been retracted.')

    return resource


def _check_resource_permissions(resource, auth, action):
    """Check if the user has the required permission on the resource."""
    required_permission = _get_permission_for_action(action)
    _confirm_token_scope(resource, required_permission)
    if required_permission == permissions.READ:
        has_resource_permissions = resource.can_view_files(auth=auth)
    else:
        has_resource_permissions = resource.can_edit(auth=auth)

    if not (has_resource_permissions or _check_hierarchical_permissions(resource, auth, action)):
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)
    return True


def _get_permission_for_action(action):
    if action in _READ_ACTIONS:
        return permissions.READ
    if action in _WRITE_ACTIONS:
        return permissions.WRITE
    raise HTTPError(http_status.HTTP_400_BAD_REQUEST, message='Invalid action specified.')


def _confirm_token_scope(resource, required_permission):
    auth_header = request.headers.get('Authorization')
    if not (auth_header and auth_header.startswith('Bearer ')):
        return  # No token, no scope conflict

    if required_permission == permissions.READ:
        if resource.can_view_files(auth=None):
            return  # Always allow read actions for public files/valid VOL
        required_scope = resource.file_read_scope
    else:
        required_scope = resource.file_write_scope

    if required_scope not in _get_token_scopes_from_cas(auth_header):
        raise HTTPError(
            http_status.HTTP_403_FORBIDDEN, 'Provided token has insufficient scope for this action'
        )


def _get_token_scopes_from_cas(auth_header):
    client = cas.get_client()
    try:
        access_token = cas.parse_auth_header(auth_header)
        cas_resp = client.profile(access_token)
    except cas.CasError as e:
        sentry.log_exception(e)
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)

    if not cas_resp.authenticated:
        raise HTTPError(
            http_status.HTTP_403_FORBIDDEN, 'Failed to authenticate via provided Bearer Token'
        )

    return oauth_scopes.normalize_scopes(cas_resp.attributes.get('accessTokenScope', []))


def _check_hierarchical_permissions(resource, auth, action):
    # Users attempting to register projects with components might not have
    # `write` permissions for all components. This will result in a 403 for
    # all `upload` actions as well as `copyfrom` actions if the component
    # in question is not public. To get around this, we have to recursively
    # check the node's parent node to determine if they have `write`
    # permissions up the stack.
    if not isinstance(resource, AbstractNode):
        return False

    supported_actions = ['copyfrom']
    if isinstance(resource, Registration):
        supported_actions.append('upload')

    if action not in supported_actions:
        return False

    permissions_resource = resource.parent_node
    while permissions_resource:
        # Keeping legacy behavior of checking `can_edit` even though `copyfrom` is a READ action
        if permissions_resource.can_edit(auth=auth):
            return True
        permissions_resource = permissions_resource.parent_node

    return False

def _get_waterbutler_configs(resource, provider_name, file_version):
    try:
        addon_settings = resource.serialize_waterbutler_settings(provider_name)
    except AttributeError:  # No addon configured on resource for provider
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, 'Requested Provider unavailable')
    if file_version:
        # Override credentials and settings with values for correct storage region
        addon_credentials = file_version.region.waterbutler_credentials
        addon_settings.update(file_version.region.waterbutler_settings)
    else:
        addon_credentials = resource.serialize_waterbutler_credentials(provider_name)

    return addon_settings, addon_credentials


def _get_osfstorage_file_version_and_node(
    file_path: str,
    file_version_id: str = None
):  # -> tuple[FileVersion, OsfStorageFileNode]
    if not file_path:
        return None, None

    file_node = OsfStorageFileNode.load(file_path.strip('/'))
    if not (file_node and file_node.is_file):
        return None, None

    try:
        file_version = FileVersion.objects.select_related('region').get(
            basefilenode=file_node,
            identifier=file_version_id or str(file_node.versions.count())
        )
    except FileVersion.DoesNotExist:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, 'Requested File Version unavailable')

    return file_version, file_node


def _enqueue_metrics(file_version, file_node, action, auth, from_mfr=False):
    if not file_version:
        return

    if action == 'render':
        file_signals.file_viewed.send(auth=auth, fileversion=file_version, file_node=file_node)
    elif action == 'download' and not from_mfr:
        file_signals.file_downloaded.send(auth=auth, fileversion=file_version, file_node=file_node)
    return


def _construct_payload(auth, resource, credentials, waterbutler_settings):

    if isinstance(resource, Registration):
        callback_url = resource.callbacks_url
    else:
        callback_url = resource.api_url_for(
            'create_waterbutler_log',
            _absolute=True,
            _internal=True
        )

    # Construct the data dictionary for JWT encoding
    jwt_data = {
        'exp': timezone.now() + datetime.timedelta(seconds=settings.WATERBUTLER_JWT_EXPIRATION),
        'data': {
            'auth': make_auth(auth.user),
            'credentials': credentials,
            'settings': waterbutler_settings,
            'callback_url': callback_url
        }
    }

    # JWT encode the data
    encoded_jwt = jwt.encode(
        jwt_data,
        settings.WATERBUTLER_JWT_SECRET,
        algorithm=settings.WATERBUTLER_JWT_ALGORITHM
    )

    # Encrypt the encoded JWT with JWE
    decoded_encrypted_jwt = jwe.encrypt(
        encoded_jwt.encode(),
        WATERBUTLER_JWE_KEY
    ).decode()

    return {'payload': decoded_encrypted_jwt}


LOG_ACTION_MAP = {
    'move': NodeLog.FILE_MOVED,
    'copy': NodeLog.FILE_COPIED,
    'rename': NodeLog.FILE_RENAMED,
    'create': NodeLog.FILE_ADDED,
    'update': NodeLog.FILE_UPDATED,
    'delete': NodeLog.FILE_REMOVED,
    'create_folder': NodeLog.FOLDER_CREATED,
}

DOWNLOAD_ACTIONS = {
    'download_file',
    'download_zip',
}

@must_be_signed
@no_auto_transaction
@must_be_valid_project(preprints_valid=True)
def create_waterbutler_log(payload, **kwargs):
    with transaction.atomic():
        try:
            auth = payload['auth']
            # Don't log download actions
            if payload['action'] in DOWNLOAD_ACTIONS:
                guid_id = payload['metadata'].get('nid')

                node, _ = Guid.load_referent(guid_id)
                return {'status': 'success'}

            user = OSFUser.load(auth['id'])
            if user is None:
                raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

            action = LOG_ACTION_MAP[payload['action']]
        except KeyError:
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

        auth = Auth(user=user)
        node = kwargs.get('node') or kwargs.get('project') or Preprint.load(kwargs.get('nid')) or Preprint.load(kwargs.get('pid'))

        if action in (NodeLog.FILE_MOVED, NodeLog.FILE_COPIED):

            for bundle in ('source', 'destination'):
                for key in ('provider', 'materialized', 'name', 'nid'):
                    if key not in payload[bundle]:
                        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

            dest = payload['destination']
            src = payload['source']

            if src is not None and dest is not None:
                dest_path = dest['materialized']
                src_path = src['materialized']
                if dest_path.endswith('/') and src_path.endswith('/'):
                    dest_path = os.path.dirname(dest_path)
                    src_path = os.path.dirname(src_path)
                if (
                    os.path.split(dest_path)[0] == os.path.split(src_path)[0] and
                    dest['provider'] == src['provider'] and
                    dest['nid'] == src['nid'] and
                    dest['name'] != src['name']
                ):
                    action = LOG_ACTION_MAP['rename']

            destination_node = node  # For clarity
            source_node = AbstractNode.load(src['nid']) or Preprint.load(src['nid'])

            # We return provider fullname so we need to load node settings, if applicable
            source = None
            if hasattr(source_node, 'get_addon'):
                source = source_node.get_addon(payload['source']['provider'])
            destination = None
            if hasattr(node, 'get_addon'):
                destination = node.get_addon(payload['destination']['provider'])

            payload['source'].update({
                'materialized': payload['source']['materialized'].lstrip('/'),
                'addon': source.config.full_name if source else 'osfstorage',
                'url': source_node.web_url_for(
                    'addon_view_or_download_file',
                    path=payload['source']['path'].lstrip('/'),
                    provider=payload['source']['provider']
                ),
                'node': {
                    '_id': source_node._id,
                    'url': source_node.url,
                    'title': source_node.title,
                }
            })

            payload['destination'].update({
                'materialized': payload['destination']['materialized'].lstrip('/'),
                'addon': destination.config.full_name if destination else 'osfstorage',
                'url': destination_node.web_url_for(
                    'addon_view_or_download_file',
                    path=payload['destination']['path'].lstrip('/'),
                    provider=payload['destination']['provider']
                ),
                'node': {
                    '_id': destination_node._id,
                    'url': destination_node.url,
                    'title': destination_node.title,
                }
            })

            if not payload.get('errors'):
                destination_node.add_log(
                    action=action,
                    auth=auth,
                    params=payload
                )

            if payload.get('email') or payload.get('errors'):
                if payload.get('email'):
                    notification_type = NotificationType.Type.FILE_OPERATION_SUCCESS
                if payload.get('errors'):
                    notification_type = NotificationType.Type.FILE_OPERATION_FAILED

                NotificationType.objects.get(name=notification_type).emit(
                    user=user,
                    subscribed_object=node,
                    event_context={
                        'action': payload['action'],
                        'source_node': source_node,
                        'destination_node': destination_node,
                        'source_path': payload['source']['materialized'],
                        'source_addon': payload['source']['addon'],
                        'destination_addon': payload['destination']['addon'],
                        'osf_support_email': settings.OSF_SUPPORT_EMAIL
                    }
                )
            if payload.get('errors'):
                # Action failed but our function succeeded
                # Bail out to avoid file_signals
                return {'status': 'success'}

        else:
            node.create_waterbutler_log(auth, action, payload)

    metadata = payload.get('metadata') or payload.get('destination')

    target_node = AbstractNode.load(metadata.get('nid'))
    if target_node and payload['action'] != 'download_file':
        update_storage_usage_with_size(payload)

    with transaction.atomic():
        file_signals.file_updated.send(target=node, user=user, payload=payload)
    return {'status': 'success'}


@file_signals.file_updated.connect
def emit_notification(self, target, user, payload, *args, **kwargs):
    notification_types = {
        'rename': NotificationType.Type.ADDON_FILE_RENAMED,
        'copy': NotificationType.Type.ADDON_FILE_COPIED,
        'create': NotificationType.Type.FILE_UPDATED,
        'move': NotificationType.Type.ADDON_FILE_MOVED,
        'delete': NotificationType.Type.FILE_REMOVED,
        'update': NotificationType.Type.FILE_UPDATED,
        'create_folder': NotificationType.Type.FOLDER_CREATED,
    }
    notification_type = notification_types[payload.get('action')]
    if notification_type not in notification_types.values():
        raise NotImplementedError(f'Notification type {notification_type} is not supported')
    NotificationType.objects.get(
        name=notification_type,
    ).emit(
        user=user,
        subscribed_object=target,
        event_context={
            'profile_image_url': user.profile_image_url(),
            'localized_timestamp': str(timezone.now()),
            'user_fullname': user.fullname,
            'url': target.absolute_url,
        }
    )

@file_signals.file_updated.connect
def addon_delete_file_node(self, target, user, payload):
    """ Get addon BaseFileNode(s), move it into the TrashedFileNode collection
    and remove it from StoredFileNode.
    Required so that the guids of deleted addon files are not re-pointed when an
    addon file or folder is moved or renamed.
    """
    event_type = payload['action']
    if event_type == 'file_removed' and payload.get('provider', None) != 'osfstorage':
        provider = payload['provider']
        path = payload['metadata']['path']
        materialized_path = payload['metadata']['materialized']
        content_type = ContentType.objects.get_for_model(target)
        if path.endswith('/'):
            folder_children = BaseFileNode.resolve_class(provider, BaseFileNode.ANY).objects.filter(
                provider=provider,
                target_object_id=target.id,
                target_content_type=content_type,
                _materialized_path__startswith=materialized_path
            )
            for item in folder_children:
                if item.kind == 'file' and not TrashedFileNode.load(item._id):
                    item.delete(user=user)
                elif item.kind == 'folder':
                    BaseFileNode.delete(item)
        else:
            try:
                file_node = BaseFileNode.resolve_class(provider, BaseFileNode.FILE).objects.get(
                    target_object_id=target.id,
                    target_content_type=content_type,
                    _materialized_path=materialized_path
                )
            except BaseFileNode.DoesNotExist:
                file_node = None

            if file_node and not TrashedFileNode.load(file_node._id):
                file_node.delete(user=user)


@file_signals.file_viewed.connect
def osfstoragefile_mark_viewed(self, auth, fileversion, file_node):
    if auth.user:
        # mark fileversion as seen
        FileVersionUserMetadata.objects.get_or_create(user=auth.user, file_version=fileversion)


@file_signals.file_viewed.connect
def osfstoragefile_update_view_analytics(self, auth, fileversion, file_node):
    resource = file_node.target
    user = getattr(auth, 'user', None)
    if hasattr(resource, 'is_contributor_or_group_member') and resource.is_contributor_or_group_member(user):
        # Don't record views by contributors
        return
    enqueue_update_analytics(
        resource,
        file_node,
        fileversion.identifier,
        'view'
    )


@file_signals.file_viewed.connect
def osfstoragefile_viewed_update_metrics(self, auth, fileversion, file_node):
    resource = file_node.target
    user = getattr(auth, 'user', None)
    if hasattr(resource, 'is_contributor_or_group_member') and resource.is_contributor_or_group_member(user):
        # Don't record views by contributors
        return
    if waffle.switch_is_active(features.ELASTICSEARCH_METRICS) and isinstance(resource, Preprint):
        try:
            PreprintView.record_for_preprint(
                preprint=resource,
                user=auth.user,
                version=fileversion.identifier,
                path=file_node.path,
            )
        except es_exceptions.ConnectionError:
            log_exception()


@file_signals.file_downloaded.connect
def osfstoragefile_downloaded_update_analytics(self, auth, fileversion, file_node):
    resource = file_node.target
    if not resource.is_contributor_or_group_member(auth.user):
        version_index = int(fileversion.identifier) - 1
        enqueue_update_analytics(resource, file_node, version_index, 'download')


@file_signals.file_downloaded.connect
def osfstoragefile_downloaded_update_metrics(self, auth, fileversion, file_node):
    resource = file_node.target
    user = getattr(auth, 'user', None)
    if hasattr(resource, 'is_contributor_or_group_member') and resource.is_contributor_or_group_member(user):
        # Don't record downloads by contributors
        return
    if waffle.switch_is_active(features.ELASTICSEARCH_METRICS) and isinstance(resource, Preprint):
        try:
            PreprintDownload.record_for_preprint(
                preprint=resource,
                user=auth.user,
                version=fileversion.identifier,
                path=file_node.path,
            )
        except es_exceptions.ConnectionError:
            log_exception()


@must_be_valid_project
def addon_view_or_download_file_legacy(**kwargs):
    query_params = request.args.to_dict()
    node = kwargs.get('node') or kwargs['project']

    action = query_params.pop('action', 'view')
    provider = kwargs.get('provider', 'osfstorage')

    if kwargs.get('path'):
        path = kwargs['path']
    elif kwargs.get('fid'):
        path = kwargs['fid']

    if 'download' in request.path or request.path.startswith('/api/v1/'):
        action = 'download'

    if kwargs.get('vid'):
        query_params['version'] = kwargs['vid']

    # If provider is OSFstorage, check existence of requested file in the filetree
    # This prevents invalid GUIDs from being created
    if provider == 'osfstorage':
        node_settings = node.get_addon('osfstorage')

        try:
            path = node_settings.get_root().find_child_by_name(path)._id
        except OsfStorageFileNode.DoesNotExist:
            raise HTTPError(
                404, data=dict(
                    message_short='File not found',
                    message_long='You requested a file that does not exist.'
                )
            )

    return redirect(
        node.web_url_for(
            'addon_view_or_download_file',
            path=path,
            provider=provider,
            action=action,
            **query_params
        ),
        code=http_status.HTTP_301_MOVED_PERMANENTLY
    )

@must_be_contributor_or_public
def addon_deleted_file(auth, target, error_type='BLAME_PROVIDER', **kwargs):
    """Shows a nice error message to users when they try to view a deleted file
    """
    # Allow file_node to be passed in so other views can delegate to this one
    file_node = kwargs.get('file_node') or TrashedFileNode.load(kwargs.get('trashed_id'))

    deleted_by, deleted_on, deleted = None, None, None
    if isinstance(file_node, TrashedFileNode):
        deleted_by = file_node.deleted_by
        deleted_by_guid = file_node.deleted_by._id if deleted_by else None
        deleted_on = file_node.deleted_on.strftime('%c') + ' UTC'
        deleted = deleted_on
        if getattr(file_node, 'suspended', False):
            error_type = 'FILE_SUSPENDED'
        elif file_node.deleted_by is None or (auth.private_key and auth.private_link.anonymous):
            if file_node.provider == 'osfstorage':
                error_type = 'FILE_GONE_ACTOR_UNKNOWN'
            else:
                error_type = 'BLAME_PROVIDER'
        else:
            error_type = 'FILE_GONE'
    else:
        error_type = 'DONT_KNOW'

    file_path = kwargs.get('path', file_node.path)
    file_name = file_node.name or os.path.basename(file_path)
    file_name_title, file_name_ext = os.path.splitext(file_name)
    provider_full = settings.ADDONS_AVAILABLE_DICT[file_node.provider].full_name
    try:
        file_guid = file_node.get_guid()._id
    except AttributeError:
        file_guid = None

    format_params = dict(
        file_name=markupsafe.escape(file_name),
        deleted_by=markupsafe.escape(getattr(deleted_by, 'fullname', None)),
        deleted_on=markupsafe.escape(deleted_on),
        provider=markupsafe.escape(provider_full),
        deleted=markupsafe.escape(deleted)
    )
    if deleted_by:
        format_params['deleted_by_guid'] = markupsafe.escape(deleted_by_guid)

    error_msg = ERROR_MESSAGES[error_type].format(**format_params)
    if isinstance(target, AbstractNode):
        error_msg += format_last_known_metadata(auth, target, file_node, error_type)
        ret = serialize_node(target, auth, primary=True)
        ret.update(rubeus.collect_addon_assets(target))
        ret.update({
            'error': error_msg,
            'urls': {
                'render': None,
                'sharejs': None,
                'mfr': get_mfr_url(target, file_node.provider),
                'profile_image': get_profile_image_url(auth.user, 25),
                'files': target.web_url_for('collect_file_trees'),
            },
            'extra': {},
            'size': 9966699,  # Prevent file from being edited, just in case
            'sharejs_uuid': None,
            'file_name': file_name,
            'file_path': file_path,
            'file_name_title': file_name_title,
            'file_name_ext': file_name_ext,
            'target_deleted': getattr(target, 'is_deleted', False),
            'version_id': None,
            'file_guid': file_guid,
            'file_id': file_node._id,
            'preprint_word': file_node.provider.preprint_word,
            'materialized_path': file_node.materialized_path or file_path,
            'private': getattr(target.get_addon(file_node.provider), 'is_private', False),
            'file_tags': list(file_node.tags.filter(system=False).values_list('name', flat=True)) if not file_node._state.adding else [],  # Only access ManyRelatedManager if saved
            'allow_comments': file_node.provider in settings.ADDONS_COMMENTABLE,
        })
    else:
        # TODO - serialize deleted metadata for future types of deleted file targets
        ret = {'error': error_msg}

    return ret, http_status.HTTP_410_GONE


@must_be_contributor_or_public
def addon_view_or_download_file(auth, path, provider, **kwargs):
    extras = request.args.to_dict()
    extras.pop('_', None)  # Clean up our url params a bit
    action = extras.get('action', 'view')
    guid = kwargs.get('guid')
    guid_target, _ = Guid.load_referent(guid)
    target = guid_target or kwargs.get('node') or kwargs['project']

    provider_safe = markupsafe.escape(provider)
    path_safe = markupsafe.escape(path)

    if not path:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    if hasattr(target, 'get_addon'):
        node_addon = target.get_addon(provider)
        if flag_is_active(request, features.ENABLE_GV):
            if not isinstance(node_addon, EphemeralNodeSettings) and provider != 'osfstorage':
                object_text = markupsafe.escape(getattr(target, 'project_or_component', 'this object'))
                raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data={
                    'message_short': 'Bad Request',
                    'message_long': f'The {provider_safe} add-on containing {path_safe} is no longer connected to {object_text}.'
                })
        elif not isinstance(node_addon, BaseStorageAddon):
            object_text = markupsafe.escape(getattr(target, 'project_or_component', 'this object'))
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data={
                'message_short': 'Bad Request',
                'message_long': f'The {provider_safe} add-on containing {path_safe} is no longer connected to {object_text}.'
            })

        if not node_addon.has_auth:
            raise HTTPError(http_status.HTTP_401_UNAUTHORIZED, data={
                'message_short': 'Unauthorized',
                'message_long': f'The {provider_safe} add-on containing {path_safe} is no longer authorized.'
            })

        if not node_addon.complete:
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data={
                'message_short': 'Bad Request',
                'message_long': f'The {provider_safe} add-on containing {path_safe} is no longer configured.'
            })

    savepoint_id = transaction.savepoint()

    try:
        file_node = BaseFileNode.resolve_class(
            provider, BaseFileNode.FILE
        ).get_or_create(
            target, path, **extras
        )
    except addon_errors.QueryError as e:
        raise HTTPError(
            http_status.HTTP_400_BAD_REQUEST,
            data={
                'message_short': 'Bad Request',
                'message_long': str(e)
            }
        )
    except addon_errors.DoesNotExist as e:
        raise HTTPError(
            http_status.HTTP_404_NOT_FOUND,
            data={
                'message_short': 'Not Found',
                'message_long': str(e)
            }
        )

    # Note: Cookie is provided for authentication to waterbutler
    # it is overridden to force authentication as the current user
    # the auth header is also pass to support basic auth
    version = file_node.touch(
        request.headers.get('Authorization'),
        **dict(
            extras,
            cookie=request.cookies.get(settings.COOKIE_NAME)
        )
    )

    # There's no download action redirect to the Ember front-end file view and create guid.
    if action != 'download':
        if isinstance(target, Node) and flag_is_active(request, features.EMBER_FILE_PROJECT_DETAIL):
            guid = file_node.get_guid(create=True)
            return redirect(f'{settings.DOMAIN}{guid._id}/')
        if isinstance(target, Registration) and flag_is_active(request, features.EMBER_FILE_REGISTRATION_DETAIL):
            guid = file_node.get_guid(create=True)
            return redirect(f'{settings.DOMAIN}{guid._id}/')

    if version is None:
        # File is either deleted or unable to be found in the provider location
        # Rollback the insertion of the file_node
        transaction.savepoint_rollback(savepoint_id)
        if not file_node.pk:
            file_node = BaseFileNode.load(path)

            if not file_node:
                raise HTTPError(http_status.HTTP_404_NOT_FOUND, data={
                    'message_short': 'File Not Found',
                    'message_long': 'The requested file could not be found.'
                })

            if file_node.kind == 'folder':
                raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data={
                    'message_short': 'Bad Request',
                    'message_long': 'You cannot request a folder from this endpoint.'
                })

            # Allow osfstorage to redirect if the deep url can be used to find a valid file_node
            if file_node.provider == 'osfstorage' and not file_node.is_deleted:
                return redirect(
                    file_node.target.web_url_for('addon_view_or_download_file', path=file_node._id, provider=file_node.provider)
                )
        return addon_deleted_file(target=target, file_node=file_node, path=path, **kwargs)
    else:
        transaction.savepoint_commit(savepoint_id)

    # TODO clean up these urls and unify what is used as a version identifier
    if request.method == 'HEAD':
        return make_response(('', http_status.HTTP_302_FOUND, {
            'Location': file_node.generate_waterbutler_url(**dict(extras, direct=None, version=version.identifier, _internal=extras.get('mode') == 'render'))
        }))

    if action == 'download':
        format = extras.get('format')
        _, extension = os.path.splitext(file_node.name)
        # avoid rendering files with the same format type.
        if format and f'.{format.lower()}' != extension.lower():
            return redirect('{}/export?format={}&url={}'.format(get_mfr_url(target, provider), format, quote(file_node.generate_waterbutler_url(
                **dict(extras, direct=None, version=version.identifier, _internal=extras.get('mode') == 'render')
            ))))
        return redirect(file_node.generate_waterbutler_url(**dict(extras, direct=None, version=version.identifier, _internal=extras.get('mode') == 'render')))

    if action == 'get_guid':
        draft_id = extras.get('draft')
        draft = DraftRegistration.load(draft_id)
        if draft is None:
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data={
                'message_short': 'Bad Request',
                'message_long': 'File not associated with required object.'
            })
        guid = file_node.get_guid(create=True)
        guid.referent.save()
        return dict(guid=guid._id)

    if len(request.path.strip('/').split('/')) > 1:
        guid = file_node.get_guid(create=True)
        # NOTE: furl encoding to be verified later
        return redirect(furl(f'/{guid._id}/', args=extras).url)
    if isinstance(target, Preprint):
        # Redirecting preprint file guids to the preprint detail page
        return redirect(f'/{target._id}/')

    return addon_view_file(auth, target, file_node, version)


@collect_auth
def persistent_file_download(auth, **kwargs):
    id_or_guid = kwargs.get('fid_or_guid')
    file = BaseFileNode.active.filter(_id=id_or_guid).first()
    if not file:
        guid = Guid.load(id_or_guid)
        if not guid:
            raise HTTPError(http_status.HTTP_404_NOT_FOUND, data={
                'message_short': 'File Not Found',
                'message_long': 'The requested file could not be found.'
            })

        file = guid.referent
        if type(file) is Preprint:
            referent, _ = Guid.load_referent(id_or_guid)
            file = referent.primary_file

    if not file.is_file:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data={
            'message_long': 'Downloading folders is not permitted.'
        })

    auth_redirect = check_contributor_auth(file.target, auth,
                                           include_public=True,
                                           include_view_only_anon=True)
    if auth_redirect:
        return auth_redirect

    query_params = request.args.to_dict()

    return redirect(
        file.generate_waterbutler_url(**query_params),
        code=http_status.HTTP_302_FOUND
    )


def addon_view_file(auth, node, file_node, version):
    # TODO: resolve circular import issue
    from addons.wiki import settings as wiki_settings

    if isinstance(version, tuple):
        version, error = version
        error = error.replace('\n', '').strip()
    else:
        error = None

    ret = serialize_node(node, auth, primary=True)

    if file_node._id + '-' + version._id not in node.file_guid_to_share_uuids:
        node.file_guid_to_share_uuids[file_node._id + '-' + version._id] = uuid.uuid4()
        node.save()

    if ret['user']['can_edit']:
        sharejs_uuid = str(node.file_guid_to_share_uuids[file_node._id + '-' + version._id])
    else:
        sharejs_uuid = None

    internal_furl = furl(settings.INTERNAL_DOMAIN)
    download_url = furl(
        request.url,
        netloc=internal_furl.netloc,
        args=dict(request.args, **{
            'direct': None,
            'mode': 'render',
            'action': 'download',
            'public_file': node.is_public,
        })
    )

    mfr_url = get_mfr_url(node, file_node.provider)
    # NOTE: furl encoding to be verified later
    render_url = furl(
        mfr_url,
        path=['render'],
        args={'url': download_url.url}
    )

    version_names = BaseFileVersionsThrough.objects.filter(
        basefilenode_id=file_node.id
    ).order_by('-fileversion_id').values_list('version_name', flat=True)

    ret.update({
        'urls': {
            'render': render_url.url,
            'mfr': mfr_url,
            'sharejs': wiki_settings.SHAREJS_URL,
            'profile_image': get_profile_image_url(auth.user, 25),
            'files': node.web_url_for('collect_file_trees'),
            'archived_from': get_archived_from_url(node, file_node) if node.is_registration else None,
        },
        'error': error,
        'file_name': file_node.name,
        'file_name_title': os.path.splitext(file_node.name)[0],
        'file_name_ext': os.path.splitext(file_node.name)[1],
        'version_id': version.identifier,
        'file_path': file_node.path,
        'sharejs_uuid': sharejs_uuid,
        'provider': file_node.provider,
        'materialized_path': file_node.materialized_path,
        'extra': version.metadata.get('extra', {}),
        'size': version.size if version.size is not None else 9966699,
        'private': getattr(node.get_addon(file_node.provider), 'is_private', False),
        'file_tags': list(file_node.tags.filter(system=False).values_list('name', flat=True)) if not file_node._state.adding else [],  # Only access ManyRelatedManager if saved
        'file_guid': file_node.get_guid()._id,
        'file_id': file_node._id,
        'allow_comments': file_node.provider in settings.ADDONS_COMMENTABLE,
        'checkout_user': file_node.checkout._id if file_node.checkout else None,
        'version_names': list(version_names)
    })

    ret.update(rubeus.collect_addon_assets(node))
    return ret


def get_archived_from_url(node, file_node):
    if file_node.copied_from:
        trashed = TrashedFileNode.load(file_node.copied_from._id)
        if not trashed:
            return node.registered_from.web_url_for('addon_view_or_download_file', provider=file_node.provider, path=file_node.copied_from._id)
    return None
