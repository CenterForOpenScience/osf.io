
import httplib as http

from framework.exceptions import HTTPError
from website.project import decorators
from website.addons.dataverse.model import connect


@decorators.must_be_contributor
@decorators.must_have_addon('dataverse', 'node')
def authorize(**kwargs):

    user = kwargs['auth'].user

    node_settings = kwargs['node_addon']
    dataverse_user = user.get_addon('dataverse')

    username = user.get_addon('dataverse').dataverse_username
    password = user.get_addon('dataverse').dataverse_password

    connection = connect(username, password)

    if connection is None:
        return {'message': 'Incorrect credentials'}, 400

    # Set user for node settings
    node_settings.user = user
    node_settings.user_settings = dataverse_user

    # Set dataverse username/password
    node_settings.dataverse_username = username
    node_settings.dataverse_password = password

    node_settings.save()

    return {}


@decorators.must_be_contributor
@decorators.must_have_addon('dataverse', 'node')
def unauthorize(*args, **kwargs):

    user = kwargs['auth'].user
    node_settings = kwargs['node_addon']
    dataverse_user = node_settings.user_settings

    if dataverse_user and dataverse_user.owner != user:
        raise HTTPError(http.BAD_REQUEST)

    node_settings.unauthorize()

    return {}


@decorators.must_have_addon('dataverse', 'user')
def dataverse_delete_user(*args, **kwargs):

    dataverse_user = kwargs['user_addon']

    # Remove authorization for nodes
    for node_settings in dataverse_user.addondataversenodesettings__authorized:
        node_settings.unauthorize()

    # Revoke access
    dataverse_user.dataverse_username = None
    dataverse_user.dataverse_password = None
    dataverse_user.save()

    return {}