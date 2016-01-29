import os
import uuid
import httplib
import datetime

import jwe
import jwt
import furl
from flask import request
from flask import redirect
from flask import make_response
from modularodm.exceptions import NoResultsFound
from modularodm import Q

from framework import sentry
from framework.auth import cas
from framework.auth import Auth
from framework.auth import oauth_scopes
from framework.routing import json_renderer
from framework.sentry import log_exception
from framework.exceptions import HTTPError
from framework.transactions.context import TokuTransaction
from framework.transactions.handlers import no_auto_transaction
from framework.auth.decorators import must_be_logged_in, must_be_signed, collect_auth
from website import mails
from website import settings
from website.files.models import FileNode
from website.files.models import TrashedFileNode
from website.project import decorators
from website.addons.base import exceptions
from website.addons.base import signals as file_signals
from website.addons.base import StorageAddonBase
from website.models import User, Node, NodeLog
from website.project.model import DraftRegistration, MetaSchema
from website.util import rubeus
from website.profile.utils import get_gravatar
from website.project.decorators import must_be_valid_project, must_be_contributor_or_public
from website.project.utils import serialize_node


# import so that associated listener is instantiated and gets emails
from website.notifications.events.files import FileEvent  # noqa

FILE_GONE_ERROR_MESSAGE = u'''
<style>
.file-download{{display: none;}}
.file-share{{display: none;}}
.file-delete{{display: none;}}
</style>
<div class="alert alert-info" role="alert">
This link to the file "{file_name}" is no longer valid.
</div>'''

WATERBUTLER_JWE_KEY = jwe.kdf(settings.WATERBUTLER_JWE_SECRET.encode('utf-8'), settings.WATERBUTLER_JWE_SALT.encode('utf-8'))


@decorators.must_have_permission('write')
@decorators.must_not_be_registration
def disable_addon(auth, **kwargs):
    node = kwargs['node'] or kwargs['project']

    addon_name = kwargs.get('addon')
    if addon_name is None:
        raise HTTPError(httplib.BAD_REQUEST)

    deleted = node.delete_addon(addon_name, auth)

    return {'deleted': deleted}


@must_be_logged_in
def get_addon_user_config(**kwargs):

    user = kwargs['auth'].user

    addon_name = kwargs.get('addon')
    if addon_name is None:
        raise HTTPError(httplib.BAD_REQUEST)

    addon = user.get_addon(addon_name)
    if addon is None:
        raise HTTPError(httplib.BAD_REQUEST)

    return addon.to_json(user)


permission_map = {
    'create_folder': 'write',
    'revisions': 'read',
    'metadata': 'read',
    'download': 'read',
    'upload': 'write',
    'delete': 'write',
    'copy': 'write',
    'move': 'write',
    'copyto': 'write',
    'moveto': 'write',
    'copyfrom': 'read',
    'movefrom': 'write',
}


def check_access(node, auth, action, cas_resp):
    """Verify that user can perform requested action on resource. Raise appropriate
    error code if action cannot proceed.
    """
    permission = permission_map.get(action, None)
    if permission is None:
        raise HTTPError(httplib.BAD_REQUEST)

    if cas_resp:
        if permission == 'read':
            if node.is_public:
                return True
            required_scope = oauth_scopes.CoreScopes.NODE_FILE_READ
        else:
            required_scope = oauth_scopes.CoreScopes.NODE_FILE_WRITE
        if not cas_resp.authenticated \
           or required_scope not in oauth_scopes.normalize_scopes(cas_resp.attributes['accessTokenScope']):
            raise HTTPError(httplib.FORBIDDEN)

    if permission == 'read' and node.can_view(auth):
        return True
    if permission == 'write' and node.can_edit(auth):
        return True

    # Users attempting to register projects with components might not have
    # `write` permissions for all components. This will result in a 403 for
    # all `copyto` actions as well as `copyfrom` actions if the component
    # in question is not public. To get around this, we have to recursively
    # check the node's parent node to determine if they have `write`
    # permissions up the stack.
    # TODO(hrybacki): is there a way to tell if this is for a registration?
    # All nodes being registered that receive the `copyto` action will have
    # `node.is_registration` == True. However, we have no way of telling if
    # `copyfrom` actions are originating from a node being registered.
    # TODO This is raise UNAUTHORIZED for registrations that have not been archived yet
    if action == 'copyfrom' or (action == 'copyto' and node.is_registration):
        parent = node.parent_node
        while parent:
            if parent.can_edit(auth):
                return True
            parent = parent.parent_node

    # Users with the PREREG_ADMIN_TAG should be allowed to download files
    # from prereg challenge draft registrations.
    try:
        prereg_schema = MetaSchema.find_one(
            Q('name', 'eq', 'Prereg Challenge') &
            Q('schema_version', 'eq', 2)
        )
        allowed_nodes = [node] + node.parents
        prereg_draft_registration = DraftRegistration.find(
            Q('branched_from', 'in', [n._id for n in allowed_nodes]) &
            Q('registration_schema', 'eq', prereg_schema)
        )
        if action == 'download' and \
                    auth.user is not None and \
                    prereg_draft_registration.count() > 0 and \
                    settings.PREREG_ADMIN_TAG in auth.user.system_tags:
            return True
    except NoResultsFound:
        pass

    raise HTTPError(httplib.FORBIDDEN if auth.user else httplib.UNAUTHORIZED)


def make_auth(user):
    if user is not None:
        return {
            'id': user._id,
            'email': '{}@osf.io'.format(user._id),
            'name': user.fullname,
        }
    return {}


@collect_auth
def get_auth(auth, **kwargs):
    cas_resp = None
    if not auth.user:
        # Central Authentication Server OAuth Bearer Token
        authorization = request.headers.get('Authorization')
        if authorization and authorization.startswith('Bearer '):
            client = cas.get_client()
            try:
                access_token = cas.parse_auth_header(authorization)
                cas_resp = client.profile(access_token)
            except cas.CasError as err:
                sentry.log_exception()
                # NOTE: We assume that the request is an AJAX request
                return json_renderer(err)
            if cas_resp.authenticated:
                auth.user = User.load(cas_resp.user)

    try:
        data = jwt.decode(
            jwe.decrypt(request.args.get('payload', '').encode('utf-8'), WATERBUTLER_JWE_KEY),
            settings.WATERBUTLER_JWT_SECRET,
            options={'require_exp': True},
            algorithm=settings.WATERBUTLER_JWT_ALGORITHM
        )['data']
    except (jwt.InvalidTokenError, KeyError):
        raise HTTPError(httplib.FORBIDDEN)

    if not auth.user:
        auth.user = User.from_cookie(data.get('cookie', ''))

    try:
        action = data['action']
        node_id = data['nid']
        provider_name = data['provider']
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)

    node = Node.load(node_id)
    if not node:
        raise HTTPError(httplib.NOT_FOUND)

    check_access(node, auth, action, cas_resp)

    provider_settings = node.get_addon(provider_name)
    if not provider_settings:
        raise HTTPError(httplib.BAD_REQUEST)

    try:
        credentials = provider_settings.serialize_waterbutler_credentials()
        waterbutler_settings = provider_settings.serialize_waterbutler_settings()
    except exceptions.AddonError:
        log_exception()
        raise HTTPError(httplib.BAD_REQUEST)

    return {'payload': jwe.encrypt(jwt.encode({
        'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=settings.WATERBUTLER_JWT_EXPIRATION),
        'data': {
            'auth': make_auth(auth.user),  # A waterbutler auth dict not an Auth object
            'credentials': credentials,
            'settings': waterbutler_settings,
            'callback_url': node.api_url_for(
                ('create_waterbutler_log' if not node.is_registration else 'registration_callbacks'),
                _absolute=True,
            ),
        }
    }, settings.WATERBUTLER_JWT_SECRET, algorithm=settings.WATERBUTLER_JWT_ALGORITHM), WATERBUTLER_JWE_KEY)}


LOG_ACTION_MAP = {
    'move': NodeLog.FILE_MOVED,
    'copy': NodeLog.FILE_COPIED,
    'rename': NodeLog.FILE_RENAMED,
    'create': NodeLog.FILE_ADDED,
    'update': NodeLog.FILE_UPDATED,
    'delete': NodeLog.FILE_REMOVED,
    'create_folder': NodeLog.FOLDER_CREATED,
}


@must_be_signed
@no_auto_transaction
@must_be_valid_project
def create_waterbutler_log(payload, **kwargs):
    with TokuTransaction():
        try:
            auth = payload['auth']
            action = LOG_ACTION_MAP[payload['action']]
        except KeyError:
            raise HTTPError(httplib.BAD_REQUEST)

        user = User.load(auth['id'])
        if user is None:
            raise HTTPError(httplib.BAD_REQUEST)

        auth = Auth(user=user)
        node = kwargs['node'] or kwargs['project']

        if action in (NodeLog.FILE_MOVED, NodeLog.FILE_COPIED):

            for bundle in ('source', 'destination'):
                for key in ('provider', 'materialized', 'name', 'nid'):
                    if key not in payload[bundle]:
                        raise HTTPError(httplib.BAD_REQUEST)

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
            source_node = Node.load(payload['source']['nid'])

            source = source_node.get_addon(payload['source']['provider'])
            destination = node.get_addon(payload['destination']['provider'])

            payload['source'].update({
                'materialized': payload['source']['materialized'].lstrip('/'),
                'addon': source.config.full_name,
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
                'addon': destination.config.full_name,
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

            payload.update({
                'node': destination_node._id,
                'project': destination_node.parent_id,
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
                    source_path=payload['source']['path'],
                    destination_path=payload['source']['path'],
                    source_addon=payload['source']['addon'],
                    destination_addon=payload['destination']['addon'],
                )

            if payload.get('error'):
                # Action failed but our function succeeded
                # Bail out to avoid file_signals
                return {'status': 'success'}

        else:
            try:
                metadata = payload['metadata']
                node_addon = node.get_addon(payload['provider'])
            except KeyError:
                raise HTTPError(httplib.BAD_REQUEST)

            if node_addon is None:
                raise HTTPError(httplib.BAD_REQUEST)

            metadata['path'] = metadata['path'].lstrip('/')

            node_addon.create_waterbutler_log(auth, action, metadata)

    with TokuTransaction():
        file_signals.file_updated.send(node=node, user=user, event_type=action, payload=payload)

    return {'status': 'success'}


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
        except NoResultsFound:
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
        code=httplib.MOVED_PERMANENTLY
    )

@must_be_valid_project
@must_be_contributor_or_public
def addon_deleted_file(auth, node, **kwargs):
    """Shows a nice error message to users when they try to view
    a deleted file
    """
    # Allow file_node to be passed in so other views can delegate to this one
    trashed = kwargs.get('file_node') or TrashedFileNode.load(kwargs.get('trashed_id'))
    if not trashed:
        raise HTTPError(httplib.NOT_FOUND, {
            'message_short': 'Not Found',
            'message_long': 'This file does not exist'
        })

    ret = serialize_node(node, auth, primary=True)
    ret.update(rubeus.collect_addon_assets(node))
    ret.update({
        'urls': {
            'render': None,
            'sharejs': None,
            'mfr': settings.MFR_SERVER_URL,
            'gravatar': get_gravatar(auth.user, 25),
            'files': node.web_url_for('collect_file_trees'),
        },
        'extra': {},
        'size': 9966699,  # Prevent file from being editted, just in case
        'sharejs_uuid': None,
        'file_name': trashed.name,
        'file_path': trashed.path,
        'provider': trashed.provider,
        'materialized_path': trashed.materialized_path,
        'error': FILE_GONE_ERROR_MESSAGE.format(file_name=trashed.name),
        'private': getattr(node.get_addon(trashed.provider), 'is_private', False),
    })

    return ret, httplib.GONE


@must_be_valid_project
@must_be_contributor_or_public
def addon_view_or_download_file(auth, path, provider, **kwargs):
    extras = request.args.to_dict()
    extras.pop('_', None)  # Clean up our url params a bit
    action = extras.get('action', 'view')
    node = kwargs.get('node') or kwargs['project']

    node_addon = node.get_addon(provider)

    if not path:
        raise HTTPError(httplib.BAD_REQUEST)

    if not isinstance(node_addon, StorageAddonBase):
        raise HTTPError(httplib.BAD_REQUEST, {
            'message_short': 'Bad Request',
            'message_long': 'The add-on containing this file is no longer connected to the {}.'.format(node.project_or_component)
        })

    if not node_addon.has_auth:
        raise HTTPError(httplib.UNAUTHORIZED, {
            'message_short': 'Unauthorized',
            'message_long': 'The add-on containing this file is no longer authorized.'
        })

    if not node_addon.complete:
        raise HTTPError(httplib.BAD_REQUEST, {
            'message_short': 'Bad Request',
            'message_long': 'The add-on containing this file is no longer configured.'
        })

    file_node = FileNode.resolve_class(provider, FileNode.FILE).get_or_create(node, path)

    # Note: Cookie is provided for authentication to waterbutler
    # it is overriden to force authentication as the current user
    # the auth header is also pass to support basic auth
    version = file_node.touch(
        request.headers.get('Authorization'),
        **dict(
            extras,
            cookie=request.cookies.get(settings.COOKIE_NAME)
        )
    )

    if version is None:
        if file_node.get_guid():
            # If this file has been successfully view before but no longer exists
            # Show a nice error message
            return addon_deleted_file(file_node=file_node, **kwargs)

        raise HTTPError(httplib.NOT_FOUND, {
            'message_short': 'Not Found',
            'message_long': 'This file does not exist'
        })

    # TODO clean up these urls and unify what is used as a version identifier
    if request.method == 'HEAD':
        return make_response(('', 200, {
            'Location': file_node.generate_waterbutler_url(**dict(extras, direct=None, version=version.identifier))
        }))

    if action == 'download':
        return redirect(file_node.generate_waterbutler_url(**dict(extras, direct=None, version=version.identifier)))

    if len(request.path.strip('/').split('/')) > 1:
        guid = file_node.get_guid(create=True)
        return redirect(furl.furl('/{}/'.format(guid._id)).set(args=extras).url)

    return addon_view_file(auth, node, file_node, version)


def addon_view_file(auth, node, file_node, version):
    # TODO: resolve circular import issue
    from website.addons.wiki import settings as wiki_settings

    if isinstance(version, tuple):
        version, error = version
        error = error.replace('\n', '').strip()
    else:
        error = None

    ret = serialize_node(node, auth, primary=True)

    if file_node._id not in node.file_guid_to_share_uuids:
        node.file_guid_to_share_uuids[file_node._id] = uuid.uuid4()
        node.save()

    if ret['user']['can_edit']:
        sharejs_uuid = str(node.file_guid_to_share_uuids[file_node._id])
    else:
        sharejs_uuid = None

    download_url = furl.furl(request.url.encode('utf-8')).set(args=dict(request.args, **{
        'direct': None,
        'mode': 'render',
        'action': 'download',
    }))

    render_url = furl.furl(settings.MFR_SERVER_URL).set(
        path=['render'],
        args={'url': download_url.url}
    )

    ret.update({
        'urls': {
            'render': render_url.url,
            'mfr': settings.MFR_SERVER_URL,
            'sharejs': wiki_settings.SHAREJS_URL,
            'gravatar': get_gravatar(auth.user, 25),
            'files': node.web_url_for('collect_file_trees'),
        },
        'error': error,
        'file_name': file_node.name,
        'file_name_title': os.path.splitext(file_node.name)[0],
        'file_name_ext': os.path.splitext(file_node.name)[1],
        'file_path': file_node.path,
        'sharejs_uuid': sharejs_uuid,
        'provider': file_node.provider,
        'materialized_path': file_node.materialized_path,
        'extra': version.metadata.get('extra', {}),
        'size': version.size if version.size is not None else 9966699,
        'private': getattr(node.get_addon(file_node.provider), 'is_private', False),
        'file_tags': [tag._id for tag in file_node.tags],
        'file_id': file_node._id,
        'allow_comments': file_node.provider in settings.ADDONS_COMMENTABLE
    })

    ret.update(rubeus.collect_addon_assets(node))
    return ret
