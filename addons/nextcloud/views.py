"""Views for the node settings page."""
# -*- coding: utf-8 -*-
import httplib as http

from django.core.exceptions import ValidationError
from furl import furl
import requests
from flask import request
from framework.auth.decorators import must_be_logged_in

from addons.base import generic_views
from osf.models import ExternalAccount
from website.project.decorators import (
    must_have_addon)

import owncloud
from addons.nextcloud.models import NextcloudProvider
from addons.nextcloud.serializer import NextcloudSerializer
from addons.nextcloud import settings

SHORT_NAME = 'nextcloud'
FULL_NAME = 'Nextcloud'

nextcloud_account_list = generic_views.account_list(
    SHORT_NAME,
    NextcloudSerializer
)

nextcloud_import_auth = generic_views.import_auth(
    SHORT_NAME,
    NextcloudSerializer
)

nextcloud_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

## Config ##

@must_be_logged_in
def nextcloud_add_user_account(auth, **kwargs):
    """
        Verifies new external account credentials and adds to user's list

        This view expects `host`, `username` and `password` fields in the JSON
        body of the request.
    """

    # Ensure that Nextcloud uses https
    host_url = request.json.get('host')
    host = furl()
    host.host = host_url.rstrip('/').replace('https://', '').replace('http://', '')
    host.scheme = 'https'

    username = request.json.get('username')
    password = request.json.get('password')

    try:
        oc = owncloud.Client(host.url, verify_certs=settings.USE_SSL)
        oc.login(username, password)
        oc.logout()
    except requests.exceptions.ConnectionError:
        return {
            'message': 'Invalid Nextcloud server.'
        }, http.BAD_REQUEST
    except owncloud.owncloud.HTTPResponseError:
        return {
            'message': 'Nextcloud Login failed.'
        }, http.UNAUTHORIZED

    provider = NextcloudProvider(account=None, host=host.url,
                            username=username, password=password)
    try:
        provider.account.save()
    except ValidationError:
        # ... or get the old one
        provider.account = ExternalAccount.objects.get(
            provider=provider.short_name,
            provider_id='{}:{}'.format(host.url, username).lower()
        )
        if provider.account.oauth_key != password:
            provider.account.oauth_key = password
            provider.account.save()

    user = auth.user
    if not user.external_accounts.filter(id=provider.account.id).exists():
        user.external_accounts.add(provider.account)

    user.get_or_add_addon('nextcloud', auth=auth)
    user.save()

    return {}

@must_have_addon(SHORT_NAME, 'user')
@must_have_addon(SHORT_NAME, 'node')
def nextcloud_folder_list(node_addon, user_addon, **kwargs):
    """ Returns all the subsequent folders under the folder id passed.
        Not easily generalizable due to `path` kwarg.
    """
    path = request.args.get('path')
    return node_addon.get_folders(path=path)

def _set_folder(node_addon, folder, auth):
    node_addon.set_folder(folder['path'], auth=auth)
    node_addon.save()

nextcloud_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    NextcloudSerializer,
    _set_folder
)

nextcloud_get_config = generic_views.get_config(
    SHORT_NAME,
    NextcloudSerializer
)
