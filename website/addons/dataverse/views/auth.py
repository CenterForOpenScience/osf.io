import httplib as http

from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in
from website.addons.dataverse.client import connect_from_settings_or_401
from website.addons.dataverse.settings import HOST
from website.project import decorators
from website.util import api_url_for


@decorators.must_be_contributor
@decorators.must_have_addon('dataverse', 'node')
@decorators.must_not_be_registration
def deauthorize_dataverse(*args, **kwargs):

    node_settings = kwargs['node_addon']
    auth = kwargs['auth']

    node_settings.deauthorize(auth)
    node_settings.save()

    return {}


@decorators.must_have_addon('dataverse', 'user')
def dataverse_delete_user(*args, **kwargs):

    user_settings = kwargs['user_addon']

    user_settings.clear()
    user_settings.save()

    return {}


@must_be_logged_in
@decorators.must_have_addon('dataverse', 'user')
def dataverse_user_config_get(user_addon, auth, **kwargs):
    """View for getting a JSON representation of the logged-in user's
    Dataverse user settings.
    """
    try:
        connection = connect_from_settings_or_401(user_addon)
    except HTTPError as error:
        if error.code == 401:
            connection = None
        else:
            raise

    urls = {
        'create': api_url_for('dataverse_set_user_config'),
        'delete': api_url_for('dataverse_delete_user'),
        'apiToken': 'https://{0}/account/apitoken'.format(HOST),
    }
    return {
        'result': {
            'connected': connection is not None,
            'userHasAuth': user_addon.has_auth,
            'apiToken': user_addon.api_token,
            'urls': urls
        },
    }, http.OK