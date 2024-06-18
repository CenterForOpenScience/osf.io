import datetime
import enum
import os
import uuid

from rest_framework import status as http_status
import markupsafe
from future.moves.urllib.parse import quote
from django.utils import timezone

from flask import make_response
from flask import request
import furl
import jwe
import jwt
import waffle
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from elasticsearch import exceptions as es_exceptions

from api.caching.tasks import update_storage_usage_with_size

from addons.base import exceptions as addon_errors
from addons.base.models import BaseStorageAddon
from addons.osfstorage.models import OsfStorageFile
from addons.osfstorage.models import OsfStorageFileNode
from addons.osfstorage.utils import enqueue_update_analytics

from framework import sentry
from framework.auth import Auth
from framework.auth.decorators import collect_auth, must_be_logged_in, must_be_signed
from framework.exceptions import HTTPError
from framework.flask import redirect
from framework.sentry import log_exception
from framework.routing import proxy_url
from framework.transactions.handlers import no_auto_transaction
from website import mails
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
    DraftNode,
    Preprint,
    Node,
    NodeLog,
    Registration,
    DraftRegistration,
    Guid,
    FileVersionUserMetadata,
    FileVersion
)
from osf.metrics import PreprintView, PreprintDownload
from osf.utils import permissions
from website.profile.utils import get_profile_image_url
from website.project import decorators
from website.project.decorators import must_be_contributor_or_public, must_be_valid_project, check_contributor_auth
from website.project.utils import serialize_node
from website.util import rubeus

# import so that associated listener is instantiated and gets emails
from website.notifications.events.files import FileEvent  # noqa
from osf.utils.requests import requests_retry_session


class PermissionsResponse(enum.Enum):
    PUBLIC_RESOURCE = enum.auto()
    PERMISSION_GRANTED = enum.auto()
    PERMISSION_DENIED = enum.auto()


ERROR_MESSAGES = {'FILE_GONE': u"""
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
                  'FILE_GONE_ACTOR_UNKNOWN': u"""
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
                  'DONT_KNOW': u"""
<style>
#toggleBar{{display: none;}}
</style>
<div class="alert alert-info" role="alert">
<p>
File not found at {provider}.
</p>""",
                  'BLAME_PROVIDER': u"""
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
                  'FILE_SUSPENDED': u"""
<style>
#toggleBar{{display: none;}}
</style>
<div class="alert alert-info" role="alert">
This content has been removed."""}

WATERBUTLER_JWE_KEY = jwe.kdf(settings.WATERBUTLER_JWE_SECRET.encode('utf-8'), settings.WATERBUTLER_JWE_SALT.encode('utf-8'))


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


permission_map = {
    'create_folder': permissions.WRITE,
    'revisions': permissions.READ,
    'metadata': permissions.READ,
    'download': permissions.READ,
    'render': permissions.READ,
    'export': permissions.READ,
    'upload': permissions.WRITE,
    'delete': permissions.WRITE,
    'copy': permissions.WRITE,
    'move': permissions.WRITE,
    'copyto': permissions.WRITE,
    'moveto': permissions.WRITE,
    'copyfrom': permissions.READ,
    'movefrom': permissions.WRITE,
}


def get_permission_for_action(action):
    """Retrieve the permission level required for a given action."""
    permission = permission_map.get(action)
    if not permission:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, message='Invalid action specified.')
    return permission


def check_resource_permissions(resource, auth, action):
    """Check if the user has the required permission on the resource."""

    # Users attempting to register projects with components might not have
    # `write` permissions for all components. This will result in a 403 for
    # all `upload` actions as well as `copyfrom` actions if the component
    # in question is not public. To get around this, we have to recursively
    # check the node's parent node to determine if they have `write`
    # permissions up the stack.
    # TODO(hrybacki): is there a way to tell if this is for a registration?
    # All nodes being registered that receive the `upload` action will have
    # `node.is_registration` == True. However, we have no way of telling if
    # `copyfrom` actions are originating from a node being registered.
    # TODO This is raise UNAUTHORIZED for registrations that have not been archived yet

    required_permission = get_permission_for_action(action)
    if isinstance(resource, Registration):
        has_permission = _check_registration_permissions(resource, auth, required_permission, action)
        is_public = resource.is_public
    elif isinstance(resource, Node):
        has_permission = _check_node_permissions(resource, auth, required_permission, action)
        is_public = resource.is_public
    elif isinstance(resource, Preprint):
        has_permission = _check_preprint_permissions(resource, auth, required_permission)
        is_public = resource.verified_publishable
    elif isinstance(resource, DraftNode):
        draft_registration = resource.registered_draft.first()
        has_permission = _check_draft_registration_permissions(draft_registration, auth, required_permission)
        is_public = False
    else:
        raise NotImplementedError()

    if has_permission and _confirm_token_scopes(resource, auth, required_permission, is_public):
        return True
    return False

def _check_registration_permissions(registration, auth, permission, action):
    if permission == permissions.READ:
        return registration.registered_from.can_view(auth)
    if action in ('copyfrom', 'upload'):
        return _check_hierarchical_write_permissions(resource=registration, auth=auth)
    return registration.can_edit(auth)


def _check_node_permissions(node, auth, permission, action):
    if permission == permissions.READ:
        return node.can_view(auth)
    if node.can_edit(auth):
        return True
    if action == 'copyfrom':
        return _check_hierarchical_write_permissions(resource=node, auth=auth)


def _check_preprint_permissions(preprint, auth, permission):
    if permission == permissions.READ:
        return preprint.can_view_files(auth)
    return preprint.can_edit(auth)


def _check_draft_registration_permissions(draft_registration, auth, permission):
    if permission == permissions.READ:
        return draft_registration.can_view(auth)
    return draft_registration.can_edit(auth)


def _check_hierarchical_write_permissions(resource, auth):
    permissions_resource = resource
    while permissions_resource:
        if permissions_resource.can_edit(auth):
            return True
        permissions_resource = permissions_resource.parent_node
    return False


def _confirm_token_scopes(resource, auth, required_permission, resource_is_public):
    # Don't apply additional limitations if not authed via Bearer Token
    if not auth.token_scopes:
        return True

    action_is_read_only = (required_permission == permissions.READ)
    if action_is_read_only and resource_is_public:
        return True

    required_scope = resource.file_read_scope if action_is_read_only else resource.file_write_scope
    return required_scope in auth.token_scopes


def make_auth(user):
    if user is not None:
        return {
            'id': user._id,
            'email': '{}@osf.io'.format(user._id),
            'name': user.fullname,
        }
    return {}


def decrypt_and_decode_jwt_payload():
    try:
        payload_encrypted = request.args.get('payload', '').encode('utf-8')
        payload_decrypted = jwe.decrypt(payload_encrypted, WATERBUTLER_JWE_KEY)
        return jwt.decode(
            payload_decrypted,
            settings.WATERBUTLER_JWT_SECRET,
            options={'require_exp': True},
            algorithm=settings.WATERBUTLER_JWT_ALGORITHM
        )['data']
    except (jwt.InvalidTokenError, KeyError) as err:
        sentry.log_message(str(err))
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)


def get_authenticated_resource(resource_id):
    resource = AbstractNode.load(resource_id) or Preprint.load(resource_id)
    if not resource:
        raise HTTPError(http_status.HTTP_404_NOT_FOUND, message='Resource not found.')

    if resource.deleted:
        raise HTTPError(http_status.HTTP_410_GONE, message='Resource has been deleted.')

    return resource


def _get_osfstorage_file_version(file_node: OsfStorageFileNode, version_string: str = None) -> FileVersion:
    if not (file_node and file_node.is_file):
        return None

    try:
        return FileVersion.objects.select_related('region').get(
            basefilenode=file_node,
            identifier=version_string or str(file_node.versions.count())
        )
    except FileVersion.DoesNotExist:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, 'Requested File Version unavailable')


def _get_osfstorage_file_node(file_path: str) -> OsfStorageFileNode:
    if not file_path:
        return None

    file_id = file_path.strip('/')
    return OsfStorageFileNode.load(file_id)


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

    # Decrypt and decode the JWT payload from the request
    waterbutler_data = decrypt_and_decode_jwt_payload()

    # Authenticate the resource based on the node_id and handle potential draft nodes
    resource = get_authenticated_resource(waterbutler_data['nid'])

    # Verify the user has permission to perform the requested action on the node
    action = waterbutler_data['action']
    if not check_resource_permissions(resource, auth, action):
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)

    # Validate provider, exclude Preprints that don't have `get_addon`.
    if not isinstance(resource, Preprint):
        provider = resource.get_addon(waterbutler_data['provider'])
        if not provider:
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    else:
        provider = None

    # Get the file version from Waterbutler data, which is used for file-specific actions
    file_node = None
    fileversion = None
    if waterbutler_data['provider'] == 'osfstorage':
        file_node = _get_osfstorage_file_node(waterbutler_data.get('path'))
        fileversion = _get_osfstorage_file_version(file_node, waterbutler_data.get('version'))

    # Fetch Waterbutler credentials and settings for the resource
    credentials, waterbutler_settings = get_waterbutler_data(
        resource,
        waterbutler_data,
        fileversion,
        provider
    )

    if fileversion:
        # Trigger any file-specific signals based on the action taken (e.g., file viewed, downloaded)
        if action == 'render':
            file_signals.file_viewed.send(auth=auth, fileversion=fileversion, file_node=file_node)
        elif action == 'download':
            file_signals.file_downloaded.send(auth=auth, fileversion=fileversion, file_node=file_node)

    # Construct the response payload including the JWT
    return construct_payload(
        auth,
        resource,
        credentials,
        waterbutler_settings
    )


def get_waterbutler_data(resource, waterbutler_data, fileversion, provider):
    provider_name = waterbutler_data.get('provider')
    if isinstance(resource, Preprint):
        credentials = resource.serialize_waterbutler_credentials()
        waterbutler_settings = resource.serialize_waterbutler_settings()
    elif fileversion:
        credentials = fileversion.region.waterbutler_credentials
        waterbutler_settings = fileversion.serialize_waterbutler_settings(
            node_id=provider.owner._id,
            root_id=provider.root_node._id,
        )
    elif waffle.flag_is_active(request, features.ENABLE_GV):
        data = requests_retry_session(
            f'{settings.DOMAIN}/v1/configured_storage_addon/{provider_name}/waterbutler-config'
        )
        credentials, waterbutler_settings = data['data']
    else:
        credentials = resource.serialize_waterbutler_credentials(provider.short_name)
        waterbutler_settings = resource.serialize_waterbutler_settings(provider.short_name)

    return credentials, waterbutler_settings


def construct_payload(auth, resource, credentials, waterbutler_settings):

    if isinstance(resource, Registration):
        callback_url = resource.api_url_for(
            'registration_callbacks',
            _absolute=True,
            _internal=True
        )
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
            'auth': {
                'id': auth.user._id,
                'email': f'{auth.user._id}@osf.io',
                'name': auth.user.fullname,
            },
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
        encoded_jwt,
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

DOWNLOAD_ACTIONS = set([
    'download_file',
    'download_zip',
])

@must_be_signed
@no_auto_transaction
@must_be_valid_project(quickfiles_valid=True, preprints_valid=True)
def create_waterbutler_log(payload, **kwargs):
    with transaction.atomic():
        try:
            auth = payload['auth']
            # Don't log download actions
            if payload['action'] in DOWNLOAD_ACTIONS:
                guid = Guid.load(payload['metadata'].get('nid'))
                if guid:
                    node = guid.referent
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

            if payload.get('email') is True or payload.get('errors'):
                mails.send_mail(
                    user.username,
                    mails.FILE_OPERATION_FAILED if payload.get('errors')
                    else mails.FILE_OPERATION_SUCCESS,
                    action=payload['action'],
                    source_node=source_node,
                    destination_node=destination_node,
                    source_path=payload['source']['materialized'],
                    source_addon=payload['source']['addon'],
                    destination_addon=payload['destination']['addon'],
                    osf_support_email=settings.OSF_SUPPORT_EMAIL
                )

            if payload.get('errors'):
                # Action failed but our function succeeded
                # Bail out to avoid file_signals
                return {'status': 'success'}

        else:
            node.create_waterbutler_log(auth, action, payload)

    metadata = payload.get('metadata') or payload.get('destination')

    target_node = AbstractNode.load(metadata.get('nid'))
    if target_node and not target_node.is_quickfiles and payload['action'] != 'download_file':
        update_storage_usage_with_size(payload)

    with transaction.atomic():
        file_signals.file_updated.send(target=node, user=user, event_type=action, payload=payload)

    return {'status': 'success'}


@file_signals.file_updated.connect
def addon_delete_file_node(self, target, user, event_type, payload):
    """ Get addon BaseFileNode(s), move it into the TrashedFileNode collection
    and remove it from StoredFileNode.
    Required so that the guids of deleted addon files are not re-pointed when an
    addon file or folder is moved or renamed.
    """
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
    enqueue_update_analytics(
        resource,
        file_node,
        fileversion.identifier,
        'view'
    )


@file_signals.file_viewed.connect
def osfstoragefile_viewed_update_metrics(self, auth, fileversion, file_node):
    resource = file_node.target
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
            'provider': file_node.provider,
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
    guid_target = getattr(Guid.load(guid), 'referent', None)
    target = guid_target or kwargs.get('node') or kwargs['project']

    provider_safe = markupsafe.escape(provider)
    path_safe = markupsafe.escape(path)

    if not path:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    if hasattr(target, 'get_addon'):

        node_addon = target.get_addon(provider)

        if not isinstance(node_addon, BaseStorageAddon):
            object_text = markupsafe.escape(getattr(target, 'project_or_component', 'this object'))
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data={
                'message_short': 'Bad Request',
                'message_long': 'The {} add-on containing {} is no longer connected to {}.'.format(provider_safe, path_safe, object_text)
            })

        if not node_addon.has_auth:
            raise HTTPError(http_status.HTTP_401_UNAUTHORIZED, data={
                'message_short': 'Unauthorized',
                'message_long': 'The {} add-on containing {} is no longer authorized.'.format(provider_safe, path_safe)
            })

        if not node_addon.complete:
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data={
                'message_short': 'Bad Request',
                'message_long': 'The {} add-on containing {} is no longer configured.'.format(provider_safe, path_safe)
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
        if isinstance(target, Node) and waffle.flag_is_active(request, features.EMBER_FILE_PROJECT_DETAIL):
            guid = file_node.get_guid(create=True)
            return redirect(f'{settings.DOMAIN}{guid._id}/')
        if isinstance(target, Registration) and waffle.flag_is_active(request, features.EMBER_FILE_REGISTRATION_DETAIL):
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
        if format and '.{}'.format(format.lower()) != extension.lower():
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
        return redirect(furl.furl('/{}/'.format(guid._id)).set(args=extras).url)
    if isinstance(target, Preprint):
        # Redirecting preprint file guids to the preprint detail page
        return redirect('/{}/'.format(target._id))

    return addon_view_file(auth, target, file_node, version)


@collect_auth
def persistent_file_download(auth, **kwargs):
    id_or_guid = kwargs.get('fid_or_guid')
    file = BaseFileNode.active.filter(_id=id_or_guid).first()
    if not file:
        guid = Guid.load(id_or_guid)
        if guid:
            file = guid.referent
        else:
            raise HTTPError(http_status.HTTP_404_NOT_FOUND, data={
                'message_short': 'File Not Found',
                'message_long': 'The requested file could not be found.'
            })
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


def addon_view_or_download_quickfile(**kwargs):
    fid = kwargs.get('fid', 'NOT_AN_FID')
    file_ = OsfStorageFile.load(fid)
    if not file_:
        raise HTTPError(http_status.HTTP_404_NOT_FOUND, data={
            'message_short': 'File Not Found',
            'message_long': 'The requested file could not be found.'
        })
    return proxy_url('/project/{}/files/osfstorage/{}/'.format(file_.target._id, fid))

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

    internal_furl = furl.furl(settings.INTERNAL_DOMAIN)
    download_url = furl.furl(request.url).set(
        netloc=internal_furl.netloc,
        args=dict(request.args, **{
            'direct': None,
            'mode': 'render',
            'action': 'download',
            'public_file': node.is_public,
        })
    )

    mfr_url = get_mfr_url(node, file_node.provider)
    render_url = furl.furl(mfr_url).set(
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
