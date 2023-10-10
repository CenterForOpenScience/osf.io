"""Views for the node settings page."""
# -*- coding: utf-8 -*-
from rest_framework import status as http_status

from django.core.exceptions import ValidationError
from furl import furl
import requests
from flask import request
from framework.auth.decorators import must_be_logged_in

from addons.base import generic_views
from osf.models import ExternalAccount
from website.project.decorators import (
    must_have_addon)

import boa
from addons.boa.models import BoaProvider
from addons.boa.serializer import BoaSerializer
from addons.boa import settings

SHORT_NAME = 'boa'
FULL_NAME = 'Boa'

boa_account_list = generic_views.account_list(
    SHORT_NAME,
    BoaSerializer
)

boa_import_auth = generic_views.import_auth(
    SHORT_NAME,
    BoaSerializer
)

boa_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

## Config ##

@must_be_logged_in
def boa_add_user_account(auth, **kwargs):
    """
        Verifies new external account credentials and adds to user's list

        This view expects `host`, `username` and `password` fields in the JSON
        body of the request.
    """

    # Ensure that boa uses https
    host_url = request.json.get('host')
    host = furl()
    host.host = host_url.rstrip('/').replace('https://', '').replace('http://', '')
    host.scheme = 'https'

    username = request.json.get('username')
    password = request.json.get('password')

    try:
        b = boa.Client(host.url, verify_certs=settings.USE_SSL)
        b.login(username, password)
        b.logout()
    except requests.exceptions.ConnectionError:
        return {
            'message': 'Invalid Boa server.'
        }, http_status.HTTP_400_BAD_REQUEST
    except boa.boa.HTTPResponseError:
        return {
            'message': 'Boa Login failed.'
        }, http_status.HTTP_401_UNAUTHORIZED

    provider = BoaProvider(
        account=None, host=host.url,
        username=username, password=password
    )
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

    user.get_or_add_addon('boa', auth=auth)
    user.save()

    return {}

@must_have_addon(SHORT_NAME, 'user')
@must_have_addon(SHORT_NAME, 'node')
def boa_folder_list(node_addon, user_addon, **kwargs):
    """ Returns all the subsequent folders under the folder id passed.
        Not easily generalizable due to `path` kwarg.
    """
    path = request.args.get('path')
    return node_addon.get_folders(path=path)

def _set_folder(node_addon, folder, auth):
    node_addon.set_folder(folder['path'], auth=auth)
    node_addon.save()

boa_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    BoaSerializer,
    _set_folder
)

boa_get_config = generic_views.get_config(
    SHORT_NAME,
    BoaSerializer
)
