import httplib as http

from framework.auth.decorators import Auth, must_be_logged_in
from website.addons.dataverse.client import connect
from website.project import decorators
from website.util import api_url_for, web_url_for


@decorators.must_be_contributor
@decorators.must_have_addon('dataverse', 'node')
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
    connection = connect(
        user_addon.dataverse_username,
        user_addon.dataverse_password
    )

    urls = {
        'create': api_url_for('dataverse_set_user_config'),
        'delete': api_url_for('dataverse_delete_user'),
    }
    return {
        'result': {
            'connected': connection is not None,
            'userHasAuth': user_addon.has_auth,
            'dataverseUsername': user_addon.dataverse_username,
            'urls': urls
        },
    }, http.OK