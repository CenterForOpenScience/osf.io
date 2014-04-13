import datetime

import httplib as http

from framework import request
from framework.exceptions import HTTPError
from website.addons.dataverse.client import connect
from website.project import decorators


@decorators.must_have_addon('dataverse', 'user')
def dataverse_set_user_config(*args, **kwargs):

    user_settings = kwargs['user_addon']

    # Log in with DATAVERSE
    username = request.json.get('dataverse_username')
    password = request.json.get('dataverse_password')
    connection = connect(username, password)

    # Check for valid connection
    if connection is None:
        raise HTTPError(http.UNAUTHORIZED)

    # Credentials are valid, but there are no dataverses
    if not connection.get_dataverses():
        raise HTTPError(http.BAD_REQUEST)

    user_settings.dataverse_username = username
    user_settings.dataverse_password = password

    for node_settings in user_settings.addondataversenodesettings__authorized:
        node_settings.dataverse_username = username
        node_settings.dataverse_password = password
        node_settings.save()

    user_settings.save()


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

    auth = kwargs['auth']
    user = auth.user

    node_settings = kwargs['node_addon']
    node = node_settings.owner
    dataverse_user = node_settings.user_settings

    now = datetime.datetime.utcnow()

    # Make a connection
    connection = connect(
        node_settings.dataverse_username,
        node_settings.dataverse_password,
    )

    # Fail if user doesn't own node_settings OR if no connection is made
    if dataverse_user and dataverse_user.owner != user or connection is None:
        raise HTTPError(http.BAD_REQUEST)

    # Set selected Dataverse
    dataverses = connection.get_dataverses() or []
    old_dataverse = dataverses[node_settings.dataverse_number].title
    old_study = node_settings.study
    node_settings.dataverse_number = request.json.get('dataverse_number')
    dataverse = dataverses[node_settings.dataverse_number] if dataverses else None
    node_settings.dataverse = dataverse.title if dataverse else None

    # Set study to None if there was a study
    if old_study is not None:

        node_settings.study_hdl = None
        node_settings.study = None

        node.add_log(
            action='dataverse_study_unlinked',
            params={
                'project': node.parent_id,
                'node': node._primary_key,
                'dataverse': {
                    'dataverse': old_dataverse,
                    'study': old_study,
                }
            },
            auth=auth,
            log_date=now,
        )

    node_settings.save()

    return {}


@decorators.must_be_contributor
@decorators.must_have_addon('dataverse', 'node')
def set_study(*args, **kwargs):

    auth = kwargs['auth']
    user = auth.user

    node_settings = kwargs['node_addon']
    node = node_settings.owner
    dataverse_user = node_settings.user_settings

    now = datetime.datetime.utcnow()

    # Make a connection
    connection = connect(
        node_settings.dataverse_username,
        node_settings.dataverse_password,
    )

    if dataverse_user and dataverse_user.owner != user or connection is None:
        raise HTTPError(http.BAD_REQUEST)

    # Get current dataverse and new study
    dataverse = connection.get_dataverses()[node_settings.dataverse_number]
    hdl = request.json.get('study_hdl')

    # Set study
    if hdl != 'None':
        log_action = 'dataverse_study_linked'
        study_name = dataverse.get_study_by_hdl(hdl).get_title()

        node_settings.dataverse = dataverse.title
        node_settings.study_hdl = hdl
        node_settings.study = study_name

    else:
        log_action = 'dataverse_study_unlinked'
        study_name = node_settings.study

        node_settings.study_hdl = None
        node_settings.study = None


    node.add_log(
        action=log_action,
        params={
            'project': node.parent_id,
            'node': node._primary_key,
            'dataverse': {
                'dataverse': dataverse.title,
                'study': study_name,
            }
        },
        auth=auth,
        log_date=now,
    )

    node_settings.save()

    return {}
