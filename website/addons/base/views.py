# -*- coding: utf-8 -*-

import os
import json
import codecs
import httplib
import functools

import furl
import requests
import itsdangerous
from flask import request
from flask import redirect
from flask import make_response

from framework.auth import Auth
from framework.sessions import Session
from framework.sentry import log_exception
from framework.exceptions import HTTPError
from framework.render.tasks import build_rendered_html
from framework.auth.decorators import must_be_logged_in, must_be_signed

from website import settings
from website.project import decorators
from website.addons.base import exceptions
from website.models import User, Node, NodeLog
from website.project.utils import serialize_node
from website.project.decorators import must_be_valid_project, must_be_contributor_or_public


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


def check_file_guid(guid):

    guid_url = '/{0}/'.format(guid._id)
    if not request.path.startswith(guid_url):
        url_split = request.url.split(guid.file_url)
        try:
            guid_url += url_split[1].lstrip('/')
        except IndexError:
            pass
        return guid_url
    return None


def get_user_from_cookie(cookie):
    if not cookie:
        return None
    try:
        token = itsdangerous.Signer(settings.SECRET_KEY).unsign(cookie)
    except itsdangerous.BadSignature:
        raise HTTPError(httplib.UNAUTHORIZED)
    session = Session.load(token)
    if session is None:
        raise HTTPError(httplib.UNAUTHORIZED)
    return User.load(session.data['auth_user_id'])


permission_map = {
    'revisions': 'read',
    'metadata': 'read',
    'download': 'read',
    'upload': 'write',
    'delete': 'write',
    'copy': 'write',
    'move': 'write',
}


def check_access(node, user, action, key=None):
    """Verify that user can perform requested action on resource. Raise appropriate
    error code if action cannot proceed.
    """
    permission = permission_map.get(action, None)
    if permission is None:
        raise HTTPError(httplib.BAD_REQUEST)
    if node.has_permission(user, permission):
        return True
    if permission == 'read':
        if node.is_public or key in node.private_link_keys_active:
            return True
    code = httplib.FORBIDDEN if user else httplib.UNAUTHORIZED
    raise HTTPError(code)


def make_auth(user):
    if user is not None:
        return {
            'id': user._id,
            'email': '{}@osf.io'.format(user._id),
            'name': user.fullname,
        }
    return {}


def restrict_addrs(*addrs):
    def wrapper(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            remote = request.remote_addr
            if remote not in addrs:
                raise HTTPError(httplib.FORBIDDEN)
            return func(*args, **kwargs)
        return wrapped
    return wrapper


restrict_waterbutler = restrict_addrs(*settings.WATERBUTLER_ADDRS)


@restrict_waterbutler
def get_auth(**kwargs):
    try:
        action = request.args['action']
        cookie = request.args['cookie']
        node_id = request.args['nid']
        provider_name = request.args['provider']
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)

    view_only = request.args.get('view_only')

    user = get_user_from_cookie(cookie)

    node = Node.load(node_id)
    if not node:
        raise HTTPError(httplib.NOT_FOUND)

    check_access(node, user, action, key=view_only)

    provider_settings = node.get_addon(provider_name)
    if not provider_settings:
        raise HTTPError(httplib.BAD_REQUEST)

    try:
        credentials = provider_settings.serialize_waterbutler_credentials()
        settings = provider_settings.serialize_waterbutler_settings()
    except exceptions.AddonError:
        log_exception()
        raise HTTPError(httplib.BAD_REQUEST)

    return {
        'auth': make_auth(user),
        'credentials': credentials,
        'settings': settings,
        'callback_url': node.api_url_for(
            'create_waterbutler_log',
            _absolute=True,
        ),
    }


LOG_ACTION_MAP = {
    'create': NodeLog.FILE_ADDED,
    'update': NodeLog.FILE_UPDATED,
    'delete': NodeLog.FILE_REMOVED,
}


@must_be_signed
@restrict_waterbutler
@must_be_valid_project
def create_waterbutler_log(payload, **kwargs):
    try:
        auth = payload['auth']
        action = payload['action']
        provider = payload['provider']
        metadata = payload['metadata']
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)

    metadata['path'] = metadata['path'].lstrip('/')

    user = User.load(auth['id'])
    if user is None:
        raise HTTPError(httplib.BAD_REQUEST)
    node = kwargs['node'] or kwargs['project']
    node_addon = node.get_addon(provider)
    if node_addon is None:
        raise HTTPError(httplib.BAD_REQUEST)
    try:
        osf_action = LOG_ACTION_MAP[action]
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)
    auth = Auth(user=user)
    node_addon.create_waterbutler_log(auth, osf_action, metadata)

    return {'status': 'success'}


def get_or_start_render(file_guid, start_render=True):
    try:
        file_guid.enrich()
    except exceptions.AddonEnrichmentError as error:
        return error.as_html()

    try:
        return codecs.open(file_guid.mfr_cache_path, 'r', 'utf-8').read()
    except IOError:
        if start_render:
            # Start rendering job if requested
            build_rendered_html(
                file_guid.mfr_download_url,
                file_guid.mfr_cache_path,
                file_guid.mfr_temp_path,
                file_guid.public_download_url
            )
    return None


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
def addon_view_or_download_file(auth, path, provider, **kwargs):
    extras = request.args.to_dict()
    action = extras.get('action', 'view')
    node = kwargs.get('node') or kwargs['project']

    node_addon = node.get_addon(provider)

    if not path or not node_addon:
        raise HTTPError(httplib.BAD_REQUEST)

    if not path.startswith('/'):
        path = '/' + path

    file_guid, created = node_addon.find_or_create_file_guid(path)

    if file_guid.guid_url != request.path:
        guid_url = furl.furl(file_guid.guid_url)
        guid_url.args.update(extras)
        return redirect(guid_url)

    file_guid.maybe_set_version(**extras)

    if action == 'download':
        download_url = furl.furl(file_guid.download_url)
        download_url.args.update(extras)
        if extras.get('mode') == 'render':
            # Temp fix for IE, return a redirect to s3 or cloudfiles (one hop)
            # Or just send back the entire body
            resp = requests.get(download_url, allow_redirects=False)
            if resp.status_code == 302:
                return redirect(resp.headers['Location'])
            else:
                return make_response(resp.content)

        return redirect(download_url.url)

    return addon_view_file(auth, node, node_addon, file_guid, extras)


def addon_view_file(auth, node, node_addon, file_guid, extras):
    render_url = node.api_url_for('addon_render_file', path=file_guid.waterbutler_path.lstrip('/'), provider=file_guid.provider, **extras)

    ret = serialize_node(node, auth, primary=True)
    ret.update({
        'provider': file_guid.provider,
        'render_url': render_url,
        'file_path': file_guid.waterbutler_path,
        'files_url': node.web_url_for('collect_file_trees'),
        'rendered': get_or_start_render(file_guid),
        # Note: must be called after get_or_start_render. This is really only for github
        'extra': json.dumps(getattr(file_guid, 'extra', {})),
        #NOTE: get_or_start_render must be called first to populate name
        'file_name': getattr(file_guid, 'name', os.path.split(file_guid.waterbutler_path)[1]),
    })

    return ret


@must_be_valid_project
@must_be_contributor_or_public
def addon_render_file(auth, path, provider, **kwargs):
    node = kwargs.get('node') or kwargs['project']

    node_addon = node.get_addon(provider)

    if not path or not node_addon:
        raise HTTPError(httplib.BAD_REQUEST)

    if not path.startswith('/'):
        path = '/' + path

    file_guid, created = node_addon.find_or_create_file_guid(path)

    file_guid.maybe_set_version(**request.args.to_dict())

    return get_or_start_render(file_guid)
