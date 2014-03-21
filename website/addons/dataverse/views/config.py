"""

"""

import httplib as http

from framework import request
from framework.exceptions import HTTPError
from website.project import decorators
from website.project.views.node import _view_project
from website.addons.dataverse.model import connect


@decorators.must_have_addon('dataverse', 'user')
def dataverse_set_user_config(*args, **kwargs):

    user_settings = kwargs['user_addon']

    # Log in with DATAVERSE
    username = request.json.get('dataverse_username')
    password = request.json.get('dataverse_password')
    connection = connect(username, password)

    if connection is not None:
        user_settings.dataverse_username = username
        user_settings.dataverse_password = password
        user_settings.save()
    else:
        raise HTTPError(http.BAD_REQUEST)


# TODO: Is this needed?
# @decorators.must_be_contributor
# @decorators.must_have_addon('dataverse', 'node')
# def dataverse_set_node_config(*args, **kwargs):
#
#     # TODO: Validate
#
#     user = kwargs['auth'].user
#
#     node_settings = kwargs['node_addon']
#     dataverse_user = node_settings.user_settings
#
#     # If authorized, only owner can change settings
#     if dataverse_user and dataverse_user.owner != user:
#         raise HTTPError(http.BAD_REQUEST)
#
#     # Verify connection
#     connection = connect(
#         node_settings.dataverse_username,
#         node_settings.dataverse_password,
#     )
#     if connection is None:
#         return {'message': 'Cannot access Dataverse.'}, \
#                http.BAD_REQUEST
#
#     return {}


@decorators.must_be_contributor
@decorators.must_have_addon('dataverse', 'node')
def set_dataverse(*args, **kwargs):

    user = kwargs['auth'].user
    node_settings = kwargs['node_addon']
    dataverse_user = node_settings.user_settings

    # Make a connection
    connection = connect(
        node_settings.dataverse_username,
        node_settings.dataverse_password,
    )

    # Fail if user doesn't own node_settings OR if no connection is made
    if dataverse_user and dataverse_user.owner != user or connection is None:
        raise HTTPError(http.BAD_REQUEST)

    # Set selected Dataverse
    node_settings.dataverse_number = request.json.get('dataverse_number')
    dataverses = connection.get_dataverses() or []
    dataverse = dataverses[node_settings.dataverse_number] if dataverses else None
    node_settings.dataverse = dataverse.title if dataverse else None

    # Set study to None
    node_settings.study_hdl = None
    node_settings.study = None

    node_settings.save()

    return {}


@decorators.must_be_contributor
@decorators.must_have_addon('dataverse', 'node')
def set_study(*args, **kwargs):

    user = kwargs['auth'].user
    node_settings = kwargs['node_addon']
    dataverse_user = node_settings.user_settings

    # Make a connection
    connection = connect(
        node_settings.dataverse_username,
        node_settings.dataverse_password,
    )

    if dataverse_user and dataverse_user.owner != user or connection is None:
        raise HTTPError(http.BAD_REQUEST)

    # Get current dataverse
    dataverse = connection.get_dataverses()[node_settings.dataverse_number]

    # Set selected Study
    hdl = request.json.get('study_hdl')
    node_settings.study_hdl = hdl if hdl != 'None' else None
    node_settings.study = dataverse.get_study_by_hdl(hdl).get_title() \
        if node_settings.study_hdl else None

    node_settings.save()

    return {}
