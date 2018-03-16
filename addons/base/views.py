import datetime
import httplib
import os
import uuid
import markupsafe
import urllib
from django.utils import timezone

from flask import make_response
from flask import redirect
from flask import request
import furl
import jwe
import jwt
from django.db import transaction

from addons.base.models import BaseStorageAddon
from addons.osfstorage.models import OsfStorageFile
from addons.osfstorage.models import OsfStorageFileNode

from framework import sentry
from framework.auth import Auth
from framework.auth import cas
from framework.auth import oauth_scopes
from framework.auth.decorators import collect_auth, must_be_logged_in, must_be_signed
from framework.exceptions import HTTPError
from framework.routing import json_renderer, proxy_url
from framework.sentry import log_exception
from framework.transactions.handlers import no_auto_transaction
from website import mails
from website import settings
from addons.base import exceptions
from addons.base import signals as file_signals
from addons.base.utils import format_last_known_metadata
from osf.models import (BaseFileNode, TrashedFileNode,
                        OSFUser, AbstractNode,
                        NodeLog, DraftRegistration, MetaSchema,
                        Guid)
from website.profile.utils import get_profile_image_url
from website.project import decorators
from website.project.decorators import must_be_contributor_or_public, must_be_valid_project, check_contributor_auth
from website.ember_osf_web.decorators import ember_flag_is_active
from website.project.utils import serialize_node
from website.settings import MFR_SERVER_URL
from website.util import rubeus

# import so that associated listener is instantiated and gets emails
from website.notifications.events.files import FileEvent  # noqa

ERROR_MESSAGES = {'FILE_GONE': u'''
<style>
#toggleBar{{display: none;}}
</style>
<div class="alert alert-info" role="alert">
<p>
The file "{file_name}" stored on {provider} was deleted via the OSF.
</p>
<p>
It was deleted by <a href="/{deleted_by_guid}">{deleted_by}</a> on {deleted_on}.
</p>''',
                  'FILE_GONE_ACTOR_UNKNOWN': u'''
<style>
#toggleBar{{display: none;}}
</style>
<div class="alert alert-info" role="alert">
<p>
The file "{file_name}" stored on {provider} was deleted via the OSF.
</p>
<p>
It was deleted on {deleted_on}.
</p>''',
                  'DONT_KNOW': u'''
<style>
#toggleBar{{display: none;}}
</style>
<div class="alert alert-info" role="alert">
<p>
File not found at {provider}.
</p>''',
                  'BLAME_PROVIDER': u'''
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
</p>''',
                  'FILE_SUSPENDED': u'''
<style>
#toggleBar{{display: none;}}
</style>
<div class="alert alert-info" role="alert">
This content has been removed.'''}

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

    if permission == 'read':
        if node.can_view(auth):
            return True
        # The user may have admin privileges on a parent node, in which
        # case they should have read permissions
        if node.is_registration and node.registered_from.can_view(auth):
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

    # Users with the prereg admin permission should be allowed to download files
    # from prereg challenge draft registrations.
    try:
        prereg_schema = MetaSchema.objects.get(name='Prereg Challenge', schema_version=2)
        allowed_nodes = [node] + node.parents
        prereg_draft_registration = DraftRegistration.objects.filter(
            branched_from__in=allowed_nodes,
            registration_schema=prereg_schema
        )
        if action == 'download' and \
                    auth.user is not None and \
                    prereg_draft_registration.count() > 0 and \
                    auth.user.has_perm('osf.administer_prereg'):
            return True
    except MetaSchema.DoesNotExist:
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
                auth.user = OSFUser.load(cas_resp.user)

    try:
        data = jwt.decode(
            jwe.decrypt(request.args.get('payload', '').encode('utf-8'), WATERBUTLER_JWE_KEY),
            settings.WATERBUTLER_JWT_SECRET,
            options={'require_exp': True},
            algorithm=settings.WATERBUTLER_JWT_ALGORITHM
        )['data']
    except (jwt.InvalidTokenError, KeyError) as err:
        sentry.log_message(str(err))
        raise HTTPError(httplib.FORBIDDEN)

    if not auth.user:
        auth.user = OSFUser.from_cookie(data.get('cookie', ''))

    try:
        action = data['action']
        node_id = data['nid']
        provider_name = data['provider']
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)

    node = AbstractNode.load(node_id)
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
        'exp': timezone.now() + datetime.timedelta(seconds=settings.WATERBUTLER_JWT_EXPIRATION),
        'data': {
            'auth': make_auth(auth.user),  # A waterbutler auth dict not an Auth object
            'credentials': credentials,
            'settings': waterbutler_settings,
            'callback_url': node.api_url_for(
                ('create_waterbutler_log' if not node.is_registration else 'registration_callbacks'),
                _absolute=True,
                _internal=True
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
    with transaction.atomic():
        try:
            auth = payload['auth']
            # Don't log download actions
            if payload['action'] in ('download_file', 'download_zip'):
                return {'status': 'success'}
            action = LOG_ACTION_MAP[payload['action']]
        except KeyError:
            raise HTTPError(httplib.BAD_REQUEST)

        user = OSFUser.load(auth['id'])
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
            source_node = AbstractNode.load(payload['source']['nid'])

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
                    source_path=payload['source']['materialized'],
                    destination_path=payload['source']['materialized'],
                    source_addon=payload['source']['addon'],
                    destination_addon=payload['destination']['addon'],
                    osf_support_email=settings.OSF_SUPPORT_EMAIL
                )

            if payload.get('errors'):
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

    with transaction.atomic():
        file_signals.file_updated.send(node=node, user=user, event_type=action, payload=payload)

    return {'status': 'success'}


@file_signals.file_updated.connect
def addon_delete_file_node(self, node, user, event_type, payload):
    """ Get addon BaseFileNode(s), move it into the TrashedFileNode collection
    and remove it from StoredFileNode.

    Required so that the guids of deleted addon files are not re-pointed when an
    addon file or folder is moved or renamed.
    """
    if event_type == 'file_removed' and payload.get('provider', None) != 'osfstorage':
        provider = payload['provider']
        path = payload['metadata']['path']
        materialized_path = payload['metadata']['materialized']
        if path.endswith('/'):
            folder_children = BaseFileNode.resolve_class(provider, BaseFileNode.ANY).objects.filter(
                provider=provider,
                node=node,
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
                    node=node,
                    _materialized_path=materialized_path
                )
            except BaseFileNode.DoesNotExist:
                file_node = None

            if file_node and not TrashedFileNode.load(file_node._id):
                file_node.delete(user=user)


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
        code=httplib.MOVED_PERMANENTLY
    )

@must_be_valid_project
@must_be_contributor_or_public
def addon_deleted_file(auth, node, error_type='BLAME_PROVIDER', **kwargs):
    """Shows a nice error message to users when they try to view a deleted file
    """
    # Allow file_node to be passed in so other views can delegate to this one
    file_node = kwargs.get('file_node') or TrashedFileNode.load(kwargs.get('trashed_id'))

    deleted_by, deleted_on = None, None
    if isinstance(file_node, TrashedFileNode):
        deleted_by = file_node.deleted_by
        deleted_by_guid = file_node.deleted_by._id if deleted_by else None
        deleted_on = file_node.deleted_on.strftime('%c') + ' UTC'
        if getattr(file_node, 'suspended', False):
            error_type = 'FILE_SUSPENDED'
        elif file_node.deleted_by is None or (auth.private_key and auth.private_key.anonymous):
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
        provider=markupsafe.escape(provider_full)
    )
    if deleted_by:
        format_params['deleted_by_guid'] = markupsafe.escape(deleted_by_guid)

    error_msg = ''.join([
        ERROR_MESSAGES[error_type].format(**format_params),
        format_last_known_metadata(auth, node, file_node, error_type)
    ])
    ret = serialize_node(node, auth, primary=True)
    ret.update(rubeus.collect_addon_assets(node))
    ret.update({
        'error': error_msg,
        'urls': {
            'render': None,
            'sharejs': None,
            'mfr': settings.MFR_SERVER_URL,
            'profile_image': get_profile_image_url(auth.user, 25),
            'files': node.web_url_for('collect_file_trees'),
        },
        'extra': {},
        'size': 9966699,  # Prevent file from being edited, just in case
        'sharejs_uuid': None,
        'file_name': file_name,
        'file_path': file_path,
        'file_name_title': file_name_title,
        'file_name_ext': file_name_ext,
        'version_id': None,
        'file_guid': file_guid,
        'file_id': file_node._id,
        'provider': file_node.provider,
        'materialized_path': file_node.materialized_path or file_path,
        'private': getattr(node.get_addon(file_node.provider), 'is_private', False),
        'file_tags': list(file_node.tags.filter(system=False).values_list('name', flat=True)) if not file_node._state.adding else [],  # Only access ManyRelatedManager if saved
        'allow_comments': file_node.provider in settings.ADDONS_COMMENTABLE,
    })

    return ret, httplib.GONE


@must_be_valid_project(quickfiles_valid=True)
@must_be_contributor_or_public
@ember_flag_is_active('ember_file_detail_page')
def addon_view_or_download_file(auth, path, provider, **kwargs):
    extras = request.args.to_dict()
    extras.pop('_', None)  # Clean up our url params a bit
    action = extras.get('action', 'view')
    node = kwargs.get('node') or kwargs['project']

    node_addon = node.get_addon(provider)

    provider_safe = markupsafe.escape(provider)
    path_safe = markupsafe.escape(path)
    project_safe = markupsafe.escape(node.project_or_component)

    if not path:
        raise HTTPError(httplib.BAD_REQUEST)

    if not isinstance(node_addon, BaseStorageAddon):
        raise HTTPError(httplib.BAD_REQUEST, data={
            'message_short': 'Bad Request',
            'message_long': 'The {} add-on containing {} is no longer connected to {}.'.format(provider_safe, path_safe, project_safe)
        })

    if not node_addon.has_auth:
        raise HTTPError(httplib.UNAUTHORIZED, data={
            'message_short': 'Unauthorized',
            'message_long': 'The {} add-on containing {} is no longer authorized.'.format(provider_safe, path_safe)
        })

    if not node_addon.complete:
        raise HTTPError(httplib.BAD_REQUEST, data={
            'message_short': 'Bad Request',
            'message_long': 'The {} add-on containing {} is no longer configured.'.format(provider_safe, path_safe)
        })

    savepoint_id = transaction.savepoint()
    file_node = BaseFileNode.resolve_class(provider, BaseFileNode.FILE).get_or_create(node, path)

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
        # File is either deleted or unable to be found in the provider location
        # Rollback the insertion of the file_node
        transaction.savepoint_rollback(savepoint_id)
        if not file_node.pk:
            file_node = BaseFileNode.load(path)
            # Allow osfstorage to redirect if the deep url can be used to find a valid file_node
            if file_node and file_node.provider == 'osfstorage' and not file_node.is_deleted:
                return redirect(
                    file_node.node.web_url_for('addon_view_or_download_file', path=file_node._id, provider=file_node.provider)
                )
        return addon_deleted_file(file_node=file_node, path=path, **kwargs)
    else:
        transaction.savepoint_commit(savepoint_id)

    # TODO clean up these urls and unify what is used as a version identifier
    if request.method == 'HEAD':
        return make_response(('', httplib.FOUND, {
            'Location': file_node.generate_waterbutler_url(**dict(extras, direct=None, version=version.identifier, _internal=extras.get('mode') == 'render'))
        }))

    if action == 'download':
        format = extras.get('format')
        _, extension = os.path.splitext(file_node.name)
        # avoid rendering files with the same format type.
        if format and '.{}'.format(format) != extension:
            return redirect('{}/export?format={}&url={}'.format(MFR_SERVER_URL, format, urllib.quote(file_node.generate_waterbutler_url(
                **dict(extras, direct=None, version=version.identifier, _internal=extras.get('mode') == 'render')
            ))))
        return redirect(file_node.generate_waterbutler_url(**dict(extras, direct=None, version=version.identifier, _internal=extras.get('mode') == 'render')))

    if action == 'get_guid':
        draft_id = extras.get('draft')
        draft = DraftRegistration.load(draft_id)
        if draft is None or draft.is_approved:
            raise HTTPError(httplib.BAD_REQUEST, data={
                'message_short': 'Bad Request',
                'message_long': 'File not associated with required object.'
            })
        guid = file_node.get_guid(create=True)
        guid.referent.save()
        return dict(guid=guid._id)

    if len(request.path.strip('/').split('/')) > 1:
        guid = file_node.get_guid(create=True)
        return redirect(furl.furl('/{}/'.format(guid._id)).set(args=extras).url)
    return addon_view_file(auth, node, file_node, version)


@collect_auth
def persistent_file_download(auth, **kwargs):
    id_or_guid = kwargs.get('fid_or_guid')
    file = BaseFileNode.active.filter(_id=id_or_guid).first()
    if not file:
        guid = Guid.load(id_or_guid)
        if guid:
            file = guid.referent
        else:
            raise HTTPError(httplib.NOT_FOUND, data={
                'message_short': 'File Not Found',
                'message_long': 'The requested file could not be found.'
            })
    if not file.is_file:
        raise HTTPError(httplib.BAD_REQUEST, data={
            'message_long': 'Downloading folders is not permitted.'
        })

    auth_redirect = check_contributor_auth(file.node, auth,
                                           include_public=True,
                                           include_view_only_anon=True)
    if auth_redirect:
        return auth_redirect

    query_params = request.args.to_dict()

    return redirect(
        file.generate_waterbutler_url(**query_params),
        code=httplib.FOUND
    )


def addon_view_or_download_quickfile(**kwargs):
    fid = kwargs.get('fid', 'NOT_AN_FID')
    file_ = OsfStorageFile.load(fid)
    if not file_:
        raise HTTPError(httplib.NOT_FOUND, data={
            'message_short': 'File Not Found',
            'message_long': 'The requested file could not be found.'
        })
    return proxy_url('/project/{}/files/osfstorage/{}/'.format(file_.node._id, fid))

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
    download_url = furl.furl(request.url.encode('utf-8')).set(
        netloc=internal_furl.netloc,
        args=dict(request.args, **{
            'direct': None,
            'mode': 'render',
            'action': 'download',
            'public_file': node.is_public,
        })
    )

    render_url = furl.furl(settings.MFR_SERVER_URL).set(
        path=['render'],
        args={'url': download_url.url}
    )

    ret.update({
        'urls': {
            'render': render_url.url,
            'mfr': settings.MFR_SERVER_URL,
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
        'pre_reg_checkout': is_pre_reg_checkout(node, file_node),
    })

    ret.update(rubeus.collect_addon_assets(node))
    return ret

def is_pre_reg_checkout(node, file_node):
    checkout_user = file_node.checkout
    if not checkout_user:
        return False
    if checkout_user in node.contributors:
        return False
    if checkout_user.has_perm('osf.view_prereg'):
        return node.draft_registrations_active.filter(registration_schema__name='Prereg Challenge').exists()
    return False

def get_archived_from_url(node, file_node):
    if file_node.copied_from:
        trashed = TrashedFileNode.load(file_node.copied_from._id)
        if not trashed:
            return node.registered_from.web_url_for('addon_view_or_download_file', provider=file_node.provider, path=file_node.copied_from._id)
    return None
