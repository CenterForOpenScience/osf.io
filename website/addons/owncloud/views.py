"""Views for the node settings page."""
# -*- coding: utf-8 -*-
import httplib as http

from flask import request
from modularodm import Q
from modularodm.storage.base import KeyExistsException

from framework.auth.decorators import must_be_logged_in

from website.addons.base import generic_views
from owncloud import Client as OwnCloudClient
from website.addons.owncloud.model import OwnCloudProvider
from website.addons.owncloud.settings import DEFAULT_HOSTS
from website.addons.owncloud.serializer import OwnCloudSerializer
from website.oauth.models import ExternalAccount
from website.project.decorators import (
    must_have_addon)
from website.util import rubeus, api_url_for

from website.addons.owncloud.utils import ExternalAccountConverter

SHORT_NAME = 'owncloud'
FULL_NAME = 'OwnCloud'

owncloud_account_list = generic_views.account_list(
    SHORT_NAME,
    OwnCloudSerializer
)

owncloud_import_auth = generic_views.import_auth(
    SHORT_NAME,
    OwnCloudSerializer
)

owncloud_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

owncloud_get_config = generic_views.get_config(
    SHORT_NAME,
    OwnCloudSerializer
)

def owncloud_root_folder(node_settings, auth, **kwargs):
    """Build HGrid JSON for root node. Note: include node URLs for client-side
    URL creation for uploaded files.
    """
    node = node_settings.owner
    root = rubeus.build_addon_root(
        node_settings=node_settings,
        name=node_settings.folder_name,
        permissions=auth,
        user=auth.user,
        nodeUrl=node.url,
        nodeApiUrl=node.api_url,
    )
    return [root]

@must_be_logged_in
def owncloud_user_config_get(auth, **kwargs):
    """View for getting a JSON representation of the logged-in user's
    OwnCloud user settings.
    """

    user_addon = auth.user.get_addon('owncloud')
    user_has_auth = False
    if user_addon:
        user_has_auth = user_addon.has_auth

    return {
        'result': {
            'userHasAuth': user_has_auth,
            'urls': {
                'create': api_url_for('owncloud_add_user_account'),
                'accounts': api_url_for('owncloud_account_list'),
            },
            'hosts': DEFAULT_HOSTS,
        },
    }, http.OK


## Config ##

@must_be_logged_in
def owncloud_add_user_account(auth, **kwargs):
    """Verifies new external account credentials and adds to user's list"""
    user = auth.user
    provider = OwnCloudProvider()

    host = request.json.get('host').rstrip('/')
    username = request.json.get('username')
    password = request.json.get('password')

    oc = OwnCloudClient(host, verify_certs=False)
    oc.login(username, password)
    oc.logout()
    try:
        provider.account = ExternalAccountConverter(host=host, username=username, password=password).account
        provider.account.save()
    except KeyExistsException:
        # ... or get the old one
        provider.account = ExternalAccount.find_one(
            Q('provider', 'eq', provider.short_name) &
            Q('provider_id', 'eq', host)
        )

    if provider.account not in user.external_accounts:
        user.external_accounts.append(provider.account)

    user_addon = auth.user.get_addon('owncloud')
    if not user_addon:
        user.add_addon('owncloud')
    user.save()

    # Need to ensure that the user has owncloud enabled at this point
    user.get_or_add_addon('owncloud', auth=auth)
    user.save()

    return {}

@must_have_addon(SHORT_NAME, 'user')
@must_have_addon(SHORT_NAME, 'node')
def owncloud_folder_list(node_addon, user_addon, **kwargs):
    """ Returns all the subsequent folders under the folder id passed.
        Not easily generalizable due to `path` kwarg.
    """

    node = kwargs.get('node') or node_addon.owner

    if 'path' not in request.args:
        return [{
            'path': '/',
            'kind': 'folder',
            'id': '/',
            'name': '/',
            'urls': {
                'folders': node.api_url_for('owncloud_folder_list', path='/')
            }
        }]

    path = request.args.get('path', '/')

    converted_account = ExternalAccountConverter(account=node_addon.external_account)

    c = OwnCloudClient(converted_account.host, verify_certs=False)
    c.login(converted_account.username, converted_account.password)

    ret = []
    for item in c.list(path):
        if item.file_type is 'dir':
            ret.append({
                'path': item.path,
                'kind': 'folder',
                'id': item.path,
                'name': item.path.strip('/').split('/')[-1],
                'urls': {
                    'folders': node.api_url_for('owncloud_folder_list', path=item.path)
                }
            })

    return ret

def _set_folder(node_addon, folder, auth):
    node_addon.set_folder(folder['name'], auth=auth)
    node_addon.save()

owncloud_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    OwnCloudSerializer,
    _set_folder
)
