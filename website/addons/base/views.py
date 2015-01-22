# -*- coding: utf-8 -*-

import httplib
import functools

import itsdangerous
from flask import request
from flask import redirect

from framework.auth import Auth
from framework.sessions import Session
from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in, must_be_signed

from website import settings
from website.models import User, Node, NodeLog
from website.project import decorators
from website.project.decorators import must_be_valid_project


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

    view_only = request.args.get('viewOnly')

    user = get_user_from_cookie(cookie)

    node = Node.load(node_id)
    if not node:
        raise HTTPError(httplib.NOT_FOUND)

    check_access(node, user, action, key=view_only)

    provider_settings = node.get_addon(provider_name)
    if not provider_settings:
        raise HTTPError(httplib.BAD_REQUEST)

    credentials = provider_settings.serialize_waterbutler_credentials()
    settings = provider_settings.serialize_waterbutler_settings()

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


@must_be_valid_project
def get_waterbutler_render_url(**kwargs):
    provider = request.args.get('provider')
    node = kwargs.get('node') or kwargs['project']

    node_addon = node.get_addon(provider)

    if not node_addon:
        raise HTTPError(httplib.BAD_REQUEST)

    try:
        url = node_addon.get_waterbutler_render_url(**request.args.to_dict())
    except TypeError:
        raise HTTPError(httplib.BAD_REQUEST)

    return redirect(url)
