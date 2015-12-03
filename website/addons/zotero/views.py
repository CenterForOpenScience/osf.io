# -*- coding: utf-8 -*-

from flask import request

from framework.auth.decorators import must_be_logged_in

from website.project.decorators import (
    must_be_contributor_or_public,
    must_have_permission,
    must_not_be_registration,
    must_have_addon,
)

from .provider import ZoteroCitationsProvider

@must_be_logged_in
def zotero_list_accounts_user(auth):
    """Return the list of all of the current user's authorized Zotero accounts."""

    provider = ZoteroCitationsProvider()
    return provider.user_accounts(auth.user)


@must_have_permission('write')
@must_have_addon('zotero', 'node')
def zotero_get_config(auth, node_addon, **kwargs):
    """Serialize node addon settings and relevant urls
    (see serialize_settings/serialize_urls)
    """

    provider = ZoteroCitationsProvider()

    result = provider.serializer(
        node_settings=node_addon,
        user_settings=auth.user.get_addon('zotero')
    ).serialized_node_settings
    result['validCredentials'] = provider.check_credentials(node_addon)
    return {'result': result}


@must_have_permission('write')
@must_have_addon('zotero', 'node')
@must_not_be_registration
def zotero_set_config(auth, node_addon, **kwargs):
    """Update ZoteroNodeSettings based on submitted account and folder information."""

    provider = ZoteroCitationsProvider()
    args = request.get_json()
    external_list_id = args.get('external_list_id')
    external_list_name = args.get('external_list_name')
    provider.set_config(
        node_addon,
        auth.user,
        external_list_id,
        external_list_name,
        auth,
    )
    return {
        'result': provider.serializer(
            node_settings=node_addon,
            user_settings=auth.user.get_addon('zotero'),
        ).serialized_node_settings
    }

@must_have_permission('write')
@must_have_addon('zotero', 'node')
@must_not_be_registration
def zotero_add_user_auth(auth, node_addon, **kwargs):
    """Allows for importing existing auth to ZoteroNodeSettings """

    provider = ZoteroCitationsProvider()
    external_account_id = request.get_json().get('external_account_id')
    return provider.add_user_auth(node_addon, auth.user, external_account_id)


@must_have_permission('write')
@must_have_addon('zotero', 'node')
@must_not_be_registration
def zotero_remove_user_auth(auth, node_addon, **kwargs):
    """Removes auth from ZoteroNodeSettings """

    provider = ZoteroCitationsProvider()
    return provider.remove_user_auth(node_addon, auth.user)


@must_be_contributor_or_public
@must_have_addon('zotero', 'node')
def zotero_widget(node_addon, **kwargs):
    """Collects and serializes settting needed to build the widget."""

    provider = ZoteroCitationsProvider()
    return provider.widget(node_addon)


@must_be_contributor_or_public
@must_have_addon('zotero', 'node')
def zotero_citation_list(auth, node_addon, zotero_list_id=None, **kwargs):
    """Collects a listing of folders and citations based on the
    passed zotero_list_id. If zotero_list_id is `None`, then all of the
    authorizer's folders and citations are listed.
    """

    provider = ZoteroCitationsProvider()
    show = request.args.get('view', 'all')
    return provider.citation_list(node_addon, auth.user, zotero_list_id, show)
