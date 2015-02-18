# -*- coding: utf-8 -*-

import httplib as http

from flask import request

from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in

from website.oauth.models import ExternalAccount
from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_permission
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon
from website.util import api_url_for, web_url_for

from . import utils
from .model import Mendeley

def serialize_urls(node_settings):

    node = node_settings.owner

    deauthorize = None
    if node_settings.external_account:
        deauthorize = node.api_url_for('mendeley_remove_user_auth')

    return {
        'config': node.api_url_for('mendeley_set_config'),
        'deauthorize': deauthorize,
        'auth': api_url_for('oauth_connect',
                            service_name='mendeley'),
        'importAuth': node.api_url_for('mendeley_add_user_auth'),
        # Endpoint for fetching only folders (including root)
        'folders': node.api_url_for('mendeley_citation_list'),
        'settings': web_url_for('user_addons')
    }


def serialize_settings(node_settings, current_user):
    node_account = node_settings.external_account
    user_accounts = [account for account in current_user.external_accounts
                     if account.provider == 'mendeley']

    user_is_owner = node_account and node_account in user_accounts

    user_settings = current_user.get_addon('mendeley')
    user_has_auth = user_settings and user_accounts

    user_account_id = None
    if user_has_auth:
        user_account_id = user_accounts[0]._id

    result = {
        'nodeHasAuth': node_settings.has_auth,
        'userIsOwner': user_is_owner,
        'userHasAuth': user_has_auth,
        'urls': serialize_urls(node_settings),
        'userAccountId': user_account_id,
    }
    if node_account is not None:
        result['folder'] = node_settings.selected_folder_name
        result['ownerName'] = node_account.display_name

    return result


@must_be_logged_in
def list_mendeley_accounts_user(auth):
    return {
        'accounts': [
            utils.serialize_account(each)
            for each in auth.user.external_accounts
            if each.provider == 'mendeley'
        ]
    }


@must_have_permission('write')
@must_have_addon('mendeley', 'node')
@must_not_be_registration
def list_citationlists_node(pid, account_id, auth, node, project, node_addon):

    account = ExternalAccount.load(account_id)
    if not account:
        raise HTTPError(http.NOT_FOUND)

    mendeley = Mendeley()
    mendeley.account = account

    return {
        'citation_lists': mendeley.citation_lists,
        'citation_tree': mendeley.citation_folder_tree,
    }


@must_have_permission('write')
@must_have_addon('mendeley', 'node')
def mendeley_get_config(auth, node_addon, **kwargs):
    """Serialize node addon settings and relevant urls
    (see serialize_settings/serialize_urls)
    """
    result = node_addon.to_json(auth.user)
    result.update(serialize_settings(node_addon, auth.user))
    return result


@must_have_permission('write')
@must_have_addon('mendeley', 'node')
@must_not_be_registration
def mendeley_add_user_auth(auth, node_addon, **kwargs):
    external_account = ExternalAccount.load(
        request.json['external_account_id']
    )
    if external_account not in auth.user.external_accounts:
        raise HTTPError(http.FORBIDDEN)

    user_addon = auth.user.get_or_add_addon('mendeley')

    node_addon.grant_oauth_access(user_addon.owner, external_account)
    node_addon.external_account = external_account
    node_addon.save()
    result = node_addon.to_json(auth.user)
    result.update(serialize_settings(node_addon, auth.user))
    return {'result': result}


@must_have_permission('write')
@must_have_addon('mendeley', 'node')
@must_not_be_registration
def mendeley_remove_user_auth(auth, node_addon, **kwargs):
    node_addon.external_account = None
    node_addon.mendeley_list_id = None
    node_addon.save()
    result = node_addon.to_json(auth.user)
    result.update(serialize_settings(node_addon, auth.user))
    return {'result': result}


@must_have_permission('write')
@must_have_addon('mendeley', 'node')
@must_not_be_registration
def mendeley_set_config(pid, auth, node, project, node_addon):
    # Ensure request has all required information
    try:
        external_account = ExternalAccount.load(
            request.json['external_account_id']
        )
        list_id = request.json['external_list_id']
    except KeyError:
        raise HTTPError(http.BAD_REQUEST)

    user = auth.user

    # User is an owner of this ExternalAccount
    if external_account in user.external_accounts:
        # grant access to the node for the Mendeley list
        node_addon.grant_oauth_access(
            user=user,
            external_account=external_account,
            metadata={'lists': list_id},
        )
    # User doesn't own the ExternalAccount
    else:
        # Make sure the node has previously been granted access
        if not node_addon.verify_oauth_access(external_account, list_id):
            raise HTTPError(http.FORBIDDEN)

    # associate the list with the node
    node_addon.external_account = external_account
    node_addon.mendeley_list_id = list_id
    node_addon.save()

    return {}


@must_be_contributor_or_public
@must_have_addon('mendeley', 'node')
def mendeley_widget(node_addon, project, node, pid, auth):
    ret = node_addon.config.to_json()
    ret.update({
        'complete': node_addon.complete,
        'list_id': node_addon.mendeley_list_id,
    })
    return ret


@must_be_contributor_or_public
@must_have_addon('mendeley', 'node')
def mendeley_citation_list(node_addon, project, node, pid, auth,
                           mendeley_list_id=None):
    """
    This function collects a listing of folders and citations based on the
    passed mendeley_list_id. If mendeley_list_id is None, then all of the
    authorizer's folders and citations are listed
    """
    view_param = request.args.get('view', 'all')

    attached_list_id = node_addon.mendeley_list_id
    list_id = mendeley_list_id

    account_folders = node_addon.api.citation_lists

    # Folders with a None type 'parent_list_id' are children of 'All Documents'
    for folder in account_folders:
        if folder.get('parent_list_id') is None:
            folder['parent_list_id'] = 'ROOT'

    node_account = node_addon.external_account
    user_accounts = [
        account for account in auth.user.external_accounts
        if account.provider == 'mendeley'
    ]
    user_is_owner = node_account in user_accounts

    # verify this list is the attached list or its descendant
    if not user_is_owner and (list_id != attached_list_id and attached_list_id is not None):
        folders = {
            (each['provider_list_id'] or 'ROOT'): each
            for each in account_folders
        }
        if list_id is None:
            ancestor_id = 'ROOT'
        else:
            ancestor_id = folders[list_id].get('parent_list_id')

        while ancestor_id != attached_list_id:
            if ancestor_id is None:
                raise HTTPError(http.FORBIDDEN)
            ancestor_id = folders[ancestor_id].get('parent_list_id')

    contents = []
    if list_id is None:
        contents = node_addon.api.get_root_folder()
    else:
        if view_param in ('all', 'folders'):
            contents += [
                {
                    'data': each,
                    'kind': 'folder',
                    'name': each['name'],
                    'id': each['id'],
                    'urls': {
                        'fetch': node_addon.owner.api_url_for(
                            'mendeley_citation_list',
                            mendeley_list_id=each['id']),
                    },
                }
                for each in account_folders
                if each.get('parent_list_id') == list_id
            ]

        if view_param in ('all', 'citations'):
            contents += [
                {
                    'csl': each,
                    'kind': 'item',
                    'id': each['id'],
                }
                for each in node_addon.api.get_list(list_id)
            ]

    return {
        'contents': contents
    }
