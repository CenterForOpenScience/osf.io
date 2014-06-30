import httplib as http

from framework import request
from framework.auth import get_current_user
from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in

from website.addons.dataverse.client import (
    connect, connect_from_settings,
    get_studies, get_study, get_dataverses, get_dataverse,
)
from website.addons.dataverse.settings import HOST
from website.project import decorators
from website.util import web_url_for, api_url_for
from website.util.sanitize import deep_ensure_clean


@decorators.must_be_valid_project
@decorators.must_have_addon('dataverse', 'node')
def dataverse_config_get(node_addon, **kwargs):
    """API that returns the serialized node settings."""
    user = get_current_user()
    return {
        'result': serialize_settings(node_addon, user),
    }, http.OK


@decorators.must_have_permission('write')
@decorators.must_have_addon('dataverse', 'user')
@decorators.must_have_addon('dataverse', 'node')
def dataverse_import_user_auth(auth, node_addon, user_addon, **kwargs):
    """Import dataverse credentials from the currently logged-in user to a node.
    """
    user = auth.user
    node_addon.set_user_auth(user_addon)
    node_addon.save()
    return {
        'result': serialize_settings(node_addon, user),
        'message': 'Successfully imported access token from profile.',
    }, http.OK


def serialize_settings(node_settings, current_user):
    """View helper that returns a dictionary representation of a
    DataverseNodeSettings record. Provides the return value for the
    dataverse config endpoints.
    """
    user_settings = node_settings.user_settings
    user_is_owner = user_settings is not None and (
        user_settings.owner._primary_key == current_user._primary_key
    )
    current_user_settings = current_user.get_addon('dataverse')
    result = {
        'nodeHasAuth': node_settings.has_auth,
        'userIsOwner': user_is_owner,
        'userHasAuth': current_user_settings is not None and current_user_settings.has_auth,
        'urls': serialize_urls(node_settings),
    }

    if node_settings.has_auth:
        # Add owner's profile info
        result['urls']['owner'] = web_url_for('profile_view_id',
            uid=user_settings.owner._primary_key)
        result.update({
            'ownerName': user_settings.owner.fullname,
            'dataverseUsername': user_settings.dataverse_username,
        })
        # Add owner's dataverse settings
        connection = connect_from_settings(user_settings)
        dataverses = get_dataverses(connection)
        result.update({
            'connected': connection is not None,
            'dataverses': [
                {'title': dataverse.title, 'alias': dataverse.alias}
                for dataverse in dataverses
            ],
            'savedDataverse': {
                'title': node_settings.dataverse,
                'alias': node_settings.dataverse_alias
            },
            'savedStudy': {
                'title': node_settings.study,
                'hdl': node_settings.study_hdl
            }
        })
    return result


def serialize_urls(node_settings):
    node = node_settings.owner
    urls = {
        'create': api_url_for('dataverse_set_user_config'),
        'set': node.api_url_for('set_dataverse_and_study'),
        'importAuth': node.api_url_for('dataverse_import_user_auth'),
        'deauthorize': node.api_url_for('deauthorize_dataverse'),
        'getStudies': node.api_url_for('dataverse_get_studies'),
        'studyPrefix': 'http://dx.doi.org/',
        'dataversePrefix': 'http://{0}/dvn/dv/'.format(HOST),
    }
    return urls


@decorators.must_have_permission('write')
@decorators.must_have_addon('dataverse', 'user')
@decorators.must_have_addon('dataverse', 'node')
def dataverse_get_studies(node_addon, **kwargs):
    alias = request.json.get('alias')
    user_settings = node_addon.user_settings

    connection = connect_from_settings(user_settings)
    dataverse = get_dataverse(connection, alias)
    studies, bad_studies = get_studies(dataverse)
    rv = {
        'studies': [{'title': study.title, 'hdl': study.doi} for study in studies],
        'badStudies': [{'hdl': bad_study.doi, 'url': 'http://dx.doi.org/' + bad_study.doi} for bad_study in bad_studies],
    }
    code = http.PARTIAL_CONTENT if bad_studies else http.OK
    return rv, code


@must_be_logged_in
def dataverse_set_user_config(auth, **kwargs):

    user = auth.user

    try:
        deep_ensure_clean(request.json)
    except ValueError:
        raise HTTPError(http.NOT_ACCEPTABLE)

    # Log in with DATAVERSE
    username = request.json.get('dataverse_username')
    password = request.json.get('dataverse_password')
    connection = connect(username, password)

    # Check for valid connection
    if connection is None:
        raise HTTPError(http.UNAUTHORIZED)

    user_addon = user.get_addon('dataverse')
    if user_addon is None:
        user.add_addon('dataverse')
        user_addon = user.get_addon('dataverse')

    user_addon.dataverse_username = username
    user_addon.dataverse_password = password
    user_addon.save()

    return {'username': username}, http.OK


@decorators.must_have_permission('write')
@decorators.must_have_addon('dataverse', 'user')
@decorators.must_have_addon('dataverse', 'node')
def set_dataverse_and_study(node_addon, auth, **kwargs):

    user_settings = node_addon.user_settings
    user = get_current_user()

    if user_settings and user_settings.owner != user:
        raise HTTPError(http.FORBIDDEN)

    try:
        deep_ensure_clean(request.json)
    except ValueError:
        raise HTTPError(http.NOT_ACCEPTABLE)

    alias = request.json.get('dataverse').get('alias')
    hdl = request.json.get('study').get('hdl')

    if hdl is None:
        return HTTPError(http.BAD_REQUEST)

    connection = connect_from_settings(user_settings)
    dataverse = get_dataverse(connection, alias)
    study = get_study(dataverse, hdl)

    node_addon.dataverse_alias = dataverse.alias
    node_addon.dataverse = dataverse.title

    node_addon.study_hdl = study.doi
    node_addon.study = study.title

    node = node_addon.owner
    node.add_log(
        action='dataverse_study_linked',
        params={
            'project': node.parent_id,
            'node': node._primary_key,
            'study': study.title,
        },
        auth=auth,
    )

    node_addon.save()

    return {'dataverse': dataverse.title, 'study': study.title}, http.OK
