"""Views for the node settings page."""
# -*- coding: utf-8 -*-

from django.core.exceptions import ValidationError
from furl import furl
from flask import request

from addons.base import generic_views
from addons.fedora.models import FedoraProvider
from addons.fedora.serializer import FedoraSerializer
from framework.auth.decorators import must_be_logged_in
from osf.models.external import ExternalAccount
from website.project.decorators import (
    must_have_addon)

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

    host = furl(request.json.get('host'))
    username = request.json.get('username')
    password = request.json.get('password')

    provider = FedoraProvider(account=None, host=host.url,
                            username=username, password=password)

    try:
        provider.account.save()
    except ValidationError:
        # ... or get the old one
        provider.account = ExternalAccount.objects.get(
            provider=provider.short_name,
            provider_id='{}:{}'.format(host.url, username).lower()
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
