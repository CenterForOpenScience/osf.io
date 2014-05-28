
from framework.auth.decorators import Auth
from website.addons.dataverse.client import connect
from website.project import decorators


@decorators.must_be_contributor
@decorators.must_have_addon('dataverse', 'node')
def authorize_dataverse(**kwargs):

    user = kwargs['auth'].user

    node_settings = kwargs['node_addon']
    user_settings = user.get_addon('dataverse')

    connection = connect(
        user_settings.dataverse_username,
        user_settings.dataverse_password,
    )

    if connection is None:
        return {'message': 'Incorrect credentials'}, 400

    # Set user for node settings
    node_settings.user_settings = user_settings
    node_settings.save()

    node = node_settings.owner
    node.add_log(
        action='dataverse_node_authorized',
        auth=Auth(user_settings.owner),
        params={
            'addon': 'dataverse',
            'project': node.parent_id,
            'node': node._primary_key,
        }
    )

    return {}


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