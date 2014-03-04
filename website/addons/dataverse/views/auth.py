
import httplib as http

from framework.exceptions import HTTPError
from website.project import decorators


@decorators.must_be_contributor
@decorators.must_have_addon('dataverse', 'node')
def authorize(**kwargs):

    user = kwargs['auth'].user

    node_settings = kwargs['node_addon']
    dataverse_user = user.get_addon('dataverse')

    node_settings.user = user
    node_settings.user_settings = dataverse_user

    username = user.get_addon('dataverse').dataverse_username
    password = user.get_addon('dataverse').dataverse_password

    connection = node_settings.user_settings.connect(
        username, password
    )

    if connection is not None:

        # Set basic dataverse fields
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

    node_settings.dataverse_username = None
    node_settings.dataverse_password = None
    node_settings.dataverse_number = 0
    node_settings.dataverse = None
    node_settings.study_hdl = None
    node_settings.study = None
    node_settings.user = None

    node_settings.save()

    return {}


@decorators.must_have_addon('dataverse', 'user')
def dataverse_delete_user(*args, **kwargs):

    dataverse_user = kwargs['user_addon']

    # # Todo: Remove webhooks
    # for node_settings in dataverse_user.addondataversenodesettings__authorized:
    #     node_settings.delete_hook()

    # Revoke access
    dataverse_user.dataverse_username = None
    dataverse_user.dataverse_password = None
    dataverse_user.save()

    return {}