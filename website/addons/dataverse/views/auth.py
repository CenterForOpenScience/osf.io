import httplib as http

from framework.auth.decorators import must_be_logged_in
from website.addons.dataverse.provider import DataverseProvider
from website.addons.dataverse.settings import DEFAULT_HOSTS
from website.project import decorators
from website.util import api_url_for


@decorators.must_be_contributor
@decorators.must_have_addon('dataverse', 'node')
@decorators.must_not_be_registration
def deauthorize_dataverse(auth, node_addon, **kwargs):
    """Remove Dataverse authorization and settings from node"""

    provider = DataverseProvider()
    provider.remove_user_auth(node_addon, auth.user)

    return {}


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
                'create': api_url_for('dataverse_add_external_account'),
                'accounts': api_url_for('dataverse_get_user_accounts'),
            },
            'hosts': DEFAULT_HOSTS,
        },
    }, http.OK
