from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError
from website.oauth.models import ExternalAccount
from website.project.decorators import must_have_permission
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon

from .model import Mendeley


@must_have_addon('mendeley', 'user')
def list_mendeley_accounts_user(auth, user_addon):
    return {
        'accounts': [
            {
                'id': account._id,
                'provider_id': account.provider_id,
                'display_name': account.display_name,
            } for account in auth.user.external_accounts
            if account.provider == 'mendeley'
        ]
    }

@must_have_permission('write')
@must_have_addon('mendeley', 'node')
@must_not_be_registration
def list_mendeley_accounts_node(pid, auth, node, project, node_addon):
    accounts = [
        each for each in auth.user.external_accounts if each.provider == 'mendeley'
    ]
    if (
        node_addon.external_account and
        node_addon.external_account not in accounts
    ):
        accounts.append(node_addon.external_account)

    return {
        'accounts': [
            {
                'id': each._id,
                'provider_id': each.provider_id,
                'display_name': each.display_name,
            } for each in accounts
        ]
    }

@must_have_permission('write')
@must_have_addon('mendeley', 'node')
@must_not_be_registration
def list_citationlists_node(pid, account_id, auth, node, project, node_addon):
    # TODO: clean up signature

    account = ExternalAccount.load(account_id)
    if not account:
        raise HTTPError(404)

    mendeley = Mendeley()
    mendeley.account = account

    return {
        'citation_lists': [each.json for each in mendeley.citation_lists]
    }