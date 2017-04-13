"""Views for the node settings page."""
# -*- coding: utf-8 -*-
import httplib as http

from furl import furl
import requests
from flask import request
from modularodm import Q
from modularodm.storage.base import KeyExistsException
from framework.auth.decorators import must_be_logged_in

from website.addons.base import generic_views
from website.oauth.models import ExternalAccount
from website.project.decorators import (
    must_have_addon)

from website.addons.fedora.model import FedoraProvider
from website.addons.fedora.serializer import FedoraSerializer
from website.addons.fedora import settings

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

fedora_root_folder = generic_views.root_folder(
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

    host_url = request.json.get('host')
    host = furl()

    host.host = host_url.rstrip('/').replace('https://', '').replace('http://', '')

    # TODO
    host.scheme = 'http'

    username = request.json.get('username')
    password = request.json.get('password')

    provider = FedoraProvider(account=None, host=host.url,
                            username=username, password=password)
    try:
        provider.account.save()
    except KeyExistsException:
        # ... or get the old one
        provider.account = ExternalAccount.find_one(
            Q('provider', 'eq', provider.short_name) &
            Q('provider_id', 'eq', username)
        )

    user = auth.user
    if provider.account not in user.external_accounts:
        user.external_accounts.append(provider.account)

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
