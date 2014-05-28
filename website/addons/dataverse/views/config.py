import datetime

import httplib as http

from framework import request
from framework.exceptions import HTTPError
from website.addons.dataverse.client import connect, get_study, get_dataverses,\
    get_dataverse
from website.project import decorators
from website.util.sanitize import deep_ensure_clean


@decorators.must_have_addon('dataverse', 'user')
def dataverse_set_user_config(*args, **kwargs):

    user_settings = kwargs['user_addon']

    # Log in with DATAVERSE
    deep_ensure_clean(request.json)
    username = request.json.get('dataverse_username')
    password = request.json.get('dataverse_password')
    connection = connect(username, password)

    # Check for valid connection
    if connection is None:
        raise HTTPError(http.UNAUTHORIZED)

    # Credentials are valid, but there are no dataverses
    if not get_dataverses(connection):
        raise HTTPError(http.BAD_REQUEST)

    user_settings.dataverse_username = username
    user_settings.dataverse_password = password

    user_settings.save()


@decorators.must_be_contributor
@decorators.must_have_addon('dataverse', 'node')
def set_dataverse(*args, **kwargs):

    auth = kwargs['auth']
    user = auth.user

    node_settings = kwargs['node_addon']
    node = node_settings.owner
    user_settings = node_settings.user_settings

    now = datetime.datetime.utcnow()

    if user_settings and user_settings.owner != user:
        raise HTTPError(http.FORBIDDEN)

    # Make a connection
    connection = connect(
        user_settings.dataverse_username,
        user_settings.dataverse_password,
    )

    if connection is None:
        raise HTTPError(http.BAD_REQUEST)

    # Set selected Dataverse
    old_dataverse = get_dataverse(connection, node_settings.dataverse_alias)
    old_study = node_settings.study
    deep_ensure_clean(request.json)
    alias = request.json.get('dataverse_alias')
    node_settings.dataverse_alias = alias if alias != 'None' else None
    dataverse = get_dataverse(connection, node_settings.dataverse_alias)
    node_settings.dataverse = dataverse.title if dataverse else None

    if node_settings.dataverse_alias and dataverse is None:
        raise HTTPError(http.BAD_REQUEST)

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
                    'dataverse': old_dataverse.title,
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
    user_settings = node_settings.user_settings

    now = datetime.datetime.utcnow()

    if user_settings and user_settings.owner != user:
        raise HTTPError(http.FORBIDDEN)

    # Make a connection
    connection = connect(
        user_settings.dataverse_username,
        user_settings.dataverse_password,
    )

    if connection is None:
        raise HTTPError(http.BAD_REQUEST)

    # Get current dataverse and new study
    deep_ensure_clean(request.json)
    dataverse = get_dataverse(connection, node_settings.dataverse_alias)
    hdl = request.json.get('study_hdl')

    # Set study
    if hdl != 'None':
        log_action = 'dataverse_study_linked'
        study = get_study(dataverse, hdl)

        if study is None:
            return HTTPError(http.BAD_REQUEST)

        node_settings.dataverse = dataverse.title
        node_settings.study_hdl = hdl
        node_settings.study = study.title

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
