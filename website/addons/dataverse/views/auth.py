import httplib as http
from flask import request

from framework.auth.decorators import must_be_logged_in
from website.addons.dataverse.provider import DataverseProvider
from website.addons.dataverse.settings import DEFAULT_HOSTS
from website.project import decorators
from website.util import api_url_for


@decorators.must_have_permission('write')
@decorators.must_have_addon('dataverse', 'node')
@decorators.must_not_be_registration
def dataverse_add_user_auth(auth, node_addon, **kwargs):
    """Allows for importing existing auth to AddonDataverseNodeSettings"""

    provider = DataverseProvider()
    external_account_id = request.get_json().get('external_account_id')
    return provider.add_user_auth(node_addon, auth.user, external_account_id)


@decorators.must_have_permission('write')
@decorators.must_have_addon('dataverse', 'node')
@decorators.must_not_be_registration
def dataverse_remove_user_auth(auth, node_addon, **kwargs):
    """Remove Dataverse authorization and settings from node"""

    provider = DataverseProvider()
    return provider.remove_user_auth(node_addon, auth.user)


@must_be_logged_in
@decorators.must_have_addon('dataverse', 'user')
def dataverse_user_config_get(user_addon, **kwargs):
    """View for getting a JSON representation of the logged-in user's
    Dataverse user settings.
    """
    return {
        'result': {
            'userHasAuth': user_addon.has_auth,
            'urls': {
                'create': api_url_for('dataverse_add_user_account'),
                'accounts': api_url_for('dataverse_get_user_accounts'),
            },
            'hosts': DEFAULT_HOSTS,
        },
    }, http.OK

