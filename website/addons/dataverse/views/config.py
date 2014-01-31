"""

"""

import httplib as http

from framework import request
from framework.exceptions import HTTPError
from website.addons.dataverse.config import TEST_CERT, TEST_HOST
from website.addons.dataverse.dvn.connection import DvnConnection
from website.project import decorators
from website.project.views.node import _view_project


@decorators.must_have_addon('dataverse', 'user')
def dataverse_set_user_config(*args, **kwargs):

    user_settings = kwargs['user_addon']

    # Log in with DATAVERSE
    username = request.json.get('dataverse_username')
    password = request.json.get('dataverse_password')
    connection = user_settings.connect(username, password)

    if connection is not None:
        user_settings.dataverse_username = username
        user_settings.dataverse_password = password
        user_settings.dv1 = connection.get_dataverses()[0].collection.title
        user_settings.save()
    else:
        raise HTTPError(http.BAD_REQUEST)


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


@decorators.must_be_contributor
@decorators.must_have_addon('dataverse', 'node')
def dataverse_set_node_config(*args, **kwargs):

    # TODO: Validate

    user = kwargs['user']

    node_settings = kwargs['node_addon']
    dataverse_user = node_settings.user_settings

    if dataverse_user and dataverse_user.owner != user:
        raise HTTPError(http.BAD_REQUEST)

    connection = dataverse_user.connect(dataverse_user.username, dataverse_user.password)

    return {}


# Todo: Delete this. For testing only
@decorators.must_be_contributor
@decorators.must_have_addon('dataverse', 'node')
def reset_dataverse(*args, **kwargs):
    node_settings = kwargs['node_addon']
    node_settings.dataverse_number = 0
    node_settings.study_number = 0
    node_settings.save()


@decorators.must_be_contributor
@decorators.must_have_addon('dataverse', 'node')
def set_dataverse(*args, **kwargs):

    node_settings = kwargs['node_addon']

    dv_num = request.json.get('dataverse_number')
    if dv_num:
        node_settings.dataverse_number = dv_num

    node_settings.study_number = request.json.get('study_number')
    node_settings.save()

    return {}

@decorators.must_be_contributor_or_public
@decorators.must_have_addon('dataverse', 'node')
def dataverse_widget(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    dataverse = node.get_addon('dataverse')

    rv = {
        'complete': True,
        'dataverse_url': dataverse.dataverse_url,
    }
    rv.update(dataverse.config.to_json())
    return rv

@decorators.must_be_contributor_or_public
def dataverse_page(**kwargs):

    user = kwargs['user']
    node = kwargs['node'] or kwargs['project']
    dataverse= node.get_addon('dataverse')

    data = _view_project(node, user)

    rv = {
        'complete': True,
        'dataverse_url': dataverse.dataverse_url,
    }
    rv.update(data)
    return rv
