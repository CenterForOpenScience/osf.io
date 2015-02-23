# -*- coding: utf-8 -*-

from flask import request

from framework.auth.decorators import must_be_logged_in

from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_permission
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon

from .provider import MendeleyCitationsProvider


@must_be_logged_in
def list_mendeley_accounts_user(auth):
    """ Returns the list of all of the current user's authorized Mendeley accounts """

    provider = MendeleyCitationsProvider()
    return provider.user_accounts(auth.user)


@must_have_permission('write')
@must_have_addon('mendeley', 'node')
def mendeley_get_config(auth, node_addon, **kwargs):
    """ Serialize node addon settings and relevant urls
    (see serialize_settings/serialize_urls)
    """

    provider = MendeleyCitationsProvider()
    return provider.serialize_settings(node_addon, auth.user)

@must_have_permission('write')
@must_have_addon('mendeley', 'node')
@must_not_be_registration
def mendeley_set_config(auth, node_addon, **kwargs):
    """ Updates MendeleyNodeSettings based on submitted account and folder information """

    provider = MendeleyCitationsProvider()
    external_account_id = request.json.get('external_account_id')
    external_list_id = request.json.get('external_list_id')
    return provider.set_config(
        node_addon,
        auth.user,
        external_account_id,
        external_list_id
    )


@must_have_permission('write')
@must_have_addon('mendeley', 'node')
@must_not_be_registration
def mendeley_add_user_auth(auth, node_addon, **kwargs):
    """ Allows for importing existing auth to MendeleyNodeSettings """

    provider = MendeleyCitationsProvider()
    external_account_id = request.json.get('external_account_id')
    return provider.add_user_auth(node_addon, auth.user, external_account_id)


@must_have_permission('write')
@must_have_addon('mendeley', 'node')
@must_not_be_registration
def mendeley_remove_user_auth(auth, node_addon, **kwargs):
    """ Removes auth from MendeleyNodeSettings """

    provider = MendeleyCitationsProvider()
    return provider.remove_user_auth(node_addon, auth.user)


@must_be_contributor_or_public
@must_have_addon('mendeley', 'node')
def mendeley_widget(node_addon, **kwargs):
    """ Collects and serializes settting needed to build the widget """

    provider = MendeleyCitationsProvider()
    return provider.widget(node_addon)


@must_be_contributor_or_public
@must_have_addon('mendeley', 'node')
def mendeley_citation_list(auth, node_addon, mendeley_list_id=None, **kwargs):
    """
    This function collects a listing of folders and citations based on the
    passed mendeley_list_id. If mendeley_list_id is None, then all of the
    authorizer's folders and citations are listed
    """

    provider = MendeleyCitationsProvider()
    show = request.args.get('view', 'all')
    return provider.citation_list(node_addon, auth.user, mendeley_list_id, show)
