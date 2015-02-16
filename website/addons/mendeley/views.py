import httplib as http

from flask import request

from framework.exceptions import HTTPError
from website.oauth.models import ExternalAccount
from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_permission
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon

from . import utils
from .model import Mendeley


@must_have_addon('mendeley', 'user')
def list_mendeley_accounts_user(auth, user_addon):
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
    # TODO: clean up signature

    account = ExternalAccount.load(account_id)
    if not account:
        raise HTTPError(http.NOT_FOUND)

    mendeley = Mendeley()
    mendeley.account = account

    return {'citation_lists': mendeley.citation_lists}


@must_have_permission('write')
@must_have_addon('mendeley', 'node')
def mendeley_get_config(auth, node_addon, **kwargs):
    return node_addon.to_json(auth.user)


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
    response = node_addon.config.to_json()
    response['complete'] = True
    return response


@must_be_contributor_or_public
@must_have_addon('mendeley', 'node')
def mendeley_citation_list(node_addon, project, node, pid, auth, mendeley_list_id=None):

    attached_list_id = node_addon.mendeley_list_id
    list_id = mendeley_list_id or attached_list_id

    account_folders = node_addon.api.citation_lists

    # verify this list is the attached list or its descendant
    if list_id != attached_list_id and attached_list_id is not None:
        folders = {
            each['provider_list_id']: each
            for each in account_folders
        }
        ancestor_id = folders[list_id].get('parent_list_id')

        while ancestor_id != attached_list_id:
            if ancestor_id is None:
                raise HTTPError(http.FORBIDDEN)
            ancestor_id = folders[ancestor_id].get('parent_list_id')

    child_lists = [
        {
            'data': each,
            'kind': 'folder',
        }
        for each in account_folders
        if each.get('parent_list_id') == list_id
    ]

    citations = [
        {
            'csl': each,
            'kind': 'item',
        }
        for each in node_addon.api.get_list(list_id)
    ]

    return {
        'contents': child_lists + citations
    }
