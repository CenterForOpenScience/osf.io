"""Views for the node settings page."""
# -*- coding: utf-8 -*-

from django.core.exceptions import ValidationError
from furl import furl
from flask import request

from addons.base import generic_views
from addons.fedora.models import FedoraProvider
from addons.fedora.serializer import FedoraSerializer
from addons.fedora.settings import USE_SSL
from framework.auth.decorators import must_be_logged_in
from osf.models.external import ExternalAccount
from website.project.decorators import (
    must_have_addon)

import httplib as http
import requests

SHORT_NAME = 'fedora'
FULL_NAME = 'Fedora'

fedora_account_list = generic_views.account_list(
    SHORT_NAME,
    FedoraSerializer
)

fedora_import_auth = generic_views.import_auth(
    SHORT_NAME,
    FedoraSerializer
)

fedora_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

## Config ##

@must_be_logged_in
def fedora_add_user_account(auth, **kwargs):
    """
        Verifies new external account credentials and adds to user's list

        This view expects `host`, `username` and `password` fields in the JSON
        body of the request.
    """

    fedora_url = request.json.get('host')
    username = request.json.get('username')
    password = request.json.get('password')

    # If Fedora URL does not start with http:// or https://, add scheme based on settings.

    if not fedora_url.startswith('http://') and not fedora_url.startswith('https://'):
        fedora_url = ('https://' if USE_SSL else 'http://') + fedora_url

    # Check Fedora URL syntax

    try:
        furl(fedora_url)
    except:
        return {
            'message': 'Invalid URL.'
        }, http.BAD_REQUEST

    # Check that this is a LDP container by issuing a HEAD request and checking Link header

    try:
        resp = requests.head(fedora_url, auth=(username, password))
    except:
        return {
            'message': 'Unable to access URL.'
        }, http.BAD_REQUEST

    else:
        if '<http://www.w3.org/ns/ldp#Container>;rel="type"' not in resp.headers.get('Link', ''):
            return {
                'message': 'Fedora login failed.'
            }, http.UNAUTHORIZED

    # Save the account

    provider = FedoraProvider(account=None, host=fedora_url,
                            username=username, password=password)

    try:
        provider.account.save()
    except ValidationError:
        # ... or get the old one
        provider.account = ExternalAccount.objects.get(
            provider=provider.short_name,
            provider_id='{}:{}'.format(fedora_url, username).lower()
        )

    user = auth.user
    if not user.external_accounts.filter(id=provider.account.id).exists():
        user.external_accounts.add(provider.account)

    user.get_or_add_addon('fedora', auth=auth)
    user.save()

    return {}

@must_have_addon(SHORT_NAME, 'user')
@must_have_addon(SHORT_NAME, 'node')
def fedora_folder_list(node_addon, user_addon, **kwargs):
    """ Returns all the subsequent folders under the folder id passed.
        Not easily generalizable due to `path` kwarg.
    """
    path = request.args.get('path')
    return node_addon.get_folders(path=path)

def _set_folder(node_addon, folder, auth):
    node_addon.set_folder(folder['path'], auth=auth)
    node_addon.save()

fedora_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    FedoraSerializer,
    _set_folder
)

fedora_get_config = generic_views.get_config(
    SHORT_NAME,
    FedoraSerializer
)
