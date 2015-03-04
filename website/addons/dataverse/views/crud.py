# -*- coding: utf-8 -*-
import httplib as http

import os
import httplib
import logging
import datetime

import requests
from flask import request, make_response

from framework.flask import redirect
from framework.exceptions import HTTPError
from framework.utils import secure_filename
from framework.auth.utils import privacy_info_handle
from website.addons.dataverse import settings

from website.addons.dataverse.client import (
    delete_file, upload_file, get_file, get_file_by_id, get_files,
    publish_dataset, get_dataset, get_dataverse, connect_from_settings,
    connect_from_settings_or_401,
)
from website.project.decorators import must_have_permission
from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon
from website.project.views.node import _view_project
from website.project.views.file import get_cache_content
from website.project.model import has_anonymous_link
from website.util import rubeus
from website.addons.dataverse.model import DataverseFile
from website.addons.dataverse.settings import HOST
from website.addons.base.views import check_file_guid

logger = logging.getLogger(__name__)


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('dataverse', 'node')
def dataverse_publish_dataset(node_addon, auth, **kwargs):

    node = node_addon.owner
    user_settings = node_addon.user_settings

    now = datetime.datetime.utcnow()

    try:
        connection = connect_from_settings_or_401(user_settings)
    except HTTPError as error:
        if error.code == httplib.UNAUTHORIZED:
            connection = None
        else:
            raise

    dataverse = get_dataverse(connection, node_addon.dataverse_alias)
    dataset = get_dataset(dataverse, node_addon.dataset_doi)

    if dataset.get_state() == 'RELEASED':
        raise HTTPError(httplib.CONFLICT)

    publish_dataset(dataset)

    # Add a log
    node.add_log(
        action='dataverse_dataset_published',
        params={
            'project': node.parent_id,
            'node': node._primary_key,
            'dataset': dataset.title,
        },
        auth=auth,
        log_date=now,
    )

    return {'dataset': dataset.title}, httplib.OK


# TODO: Temporary solution until waterbutler is implemented
@must_be_contributor_or_public
@must_have_addon('dataverse', 'node')
def dataverse_download_file(node_addon, auth, **kwargs):

    user_settings = node_addon.user_settings
    token = user_settings.api_token
    file_id = kwargs.get('path')

    fail_if_unauthorized(node_addon, auth, file_id)
    filename, content = get_file_content(file_id, token)

    # Build response
    resp = make_response(content)
    resp.headers['Content-Disposition'] = 'attachment; filename={0}'.format(
        filename
    )

    resp.headers['Content-Type'] = 'application/octet-stream'

    return resp


# TODO: Temporary solution until waterbutler is implemented
@must_be_contributor_or_public
@must_have_addon('dataverse', 'node')
def dataverse_download_file_proxy(node_addon, auth, **kwargs):

    user_settings = node_addon.user_settings
    token = user_settings.api_token
    file_id = kwargs.get('path')

    fail_if_unauthorized(node_addon, auth, file_id)
    filename, content = get_file_content(file_id, token)

    # Build response
    resp = make_response(content)
    resp.headers['Content-Disposition'] = 'attachment; filename={0}'.format(
        filename
    )

    resp.headers['Content-Type'] = 'application/octet-stream'

    return resp

@must_be_contributor_or_public
@must_have_addon('dataverse', 'node')
def dataverse_get_file_info(node_addon, auth, **kwargs):
    """API view that gets info for a file."""
    node = node_addon.owner
    user_settings = node_addon.user_settings
    token = user_settings.api_token
    file_id = kwargs.get('path')

    fail_if_unauthorized(node_addon, auth, file_id)

    anonymous = has_anonymous_link(node, auth)

    download_url = node.web_url_for('dataverse_download_file', path=file_id)
    dataverse_url = 'http://{0}/dataverse/'.format(HOST) + node_addon.dataverse_alias
    dataset_url = 'http://dx.doi.org/' + node_addon.dataset_doi
    delete_url = node.api_url_for('dataverse_delete_file', path=file_id)
    filename = get_file_content(file_id, token, name_only=True)[0]

    data = {
        'node': {
            'id': node._id,
            'title': node.title
        },
        'filename': filename,
        'dataverse': privacy_info_handle(node_addon.dataverse, anonymous),
        'dataset': privacy_info_handle(node_addon.dataset, anonymous),
        'urls': {
            'dataverse': privacy_info_handle(dataverse_url, anonymous),
            'dataset': privacy_info_handle(dataset_url, anonymous),
            'download': privacy_info_handle(download_url, anonymous),
            'delete': privacy_info_handle(delete_url, anonymous),
            'files': node.web_url_for('collect_file_trees'),
        }
    }

    return {'data': data}, httplib.OK


@must_be_contributor_or_public
@must_have_addon('dataverse', 'node')
def dataverse_view_file(node_addon, auth, **kwargs):

    node = node_addon.owner
    user_settings = node_addon.user_settings
    token = user_settings.api_token

    file_id = kwargs.get('path')

    fail_if_unauthorized(node_addon, auth, file_id)

    # lazily create a file GUID record
    file_obj, created = DataverseFile.get_or_create(node=node, path=file_id)

    redirect_url = check_file_guid(file_obj)
    if redirect_url:
        return redirect(redirect_url)

    # Get or create rendered file
    cache_file_name = '{0}.html'.format(file_id)
    rendered = get_cache_content(node_addon, cache_file_name)

    if rendered is None:
        filename, content = get_file_content(file_id, token)
        _, ext = os.path.splitext(filename)
        download_url = node.api_url_for(
            'dataverse_download_file_proxy', path=file_id
        )
        rendered = get_cache_content(
            node_addon,
            cache_file_name,
            start_render=True,
            remote_path=file_obj.file_id + ext,  # Include extension for MFR
            file_content=content,
            download_url=download_url,
        )
    else:
        filename, _ = get_file_content(file_id, token, name_only=True)

    render_url = node.api_url_for('dataverse_get_rendered_file',
                                path=file_id)
    ret = {
        'file_name': filename,
        'rendered': rendered,
        'render_url': render_url,
        'urls': {
            'render': render_url,
            'download': node.web_url_for('dataverse_download_file',
                                         path=file_id),
            'info': node.api_url_for('dataverse_get_file_info',
                                     path=file_id),
        }

    }
    ret.update(_view_project(node, auth))
    return ret


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('dataverse', 'node')
def dataverse_upload_file(node_addon, auth, **kwargs):
    node = node_addon.owner
    user_settings = node_addon.user_settings

    try:
        name = request.args['name']
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)

    now = datetime.datetime.utcnow()

    can_edit = node.can_edit(auth) and not node.is_registration
    can_view = node.can_view(auth)

    try:
        connection = connect_from_settings_or_401(user_settings)
    except HTTPError as error:
        if error.code == httplib.UNAUTHORIZED:
            connection = None
        else:
            raise

    dataverse = get_dataverse(connection, node_addon.dataverse_alias)
    dataset = get_dataset(dataverse, node_addon.dataset_doi)

    filename = secure_filename(name)
    status_code = httplib.CREATED
    old_id = None

    # Fail if file is too small (Dataverse issue)
    content = request.data
    if len(content) < 5:
        raise HTTPError(httplib.UNSUPPORTED_MEDIA_TYPE)

    # Replace file if old version exists
    old_file = get_file(dataset, filename)
    if old_file is not None:
        status_code = httplib.OK
        old_id = old_file.id
        delete_file(old_file)
        # Check if file was deleted
        if get_file_by_id(dataset, old_id) is not None:
            raise HTTPError(httplib.BAD_REQUEST)

    upload_file(dataset, filename, content)
    file = get_file(dataset, filename)

    if file is None:
        raise HTTPError(httplib.BAD_REQUEST)

    node.add_log(
        action='dataverse_file_added',
        params={
            'project': node.parent_id,
            'node': node._primary_key,
            'filename': filename,
            'path': node.web_url_for('dataverse_view_file', path=file.id),
            'dataset': dataset.title,
        },
        auth=auth,
        log_date=now,
    )

    info = {
        'addon': 'dataverse',
        'file_id': file.id,
        'old_id': old_id,
        'name': filename,
        'path': filename,
        'size': [
            len(content),
            rubeus.format_filesize(len(content))
        ],
        rubeus.KIND: rubeus.FILE,
        'urls': {
            'view': node.web_url_for('dataverse_view_file',
                                     path=file.id),
            'download': node.web_url_for('dataverse_download_file',
                                         path=file.id),
            'delete': node.api_url_for('dataverse_delete_file',
                                          path=file.id),
        },
        'permissions': {
            'view': can_view,
            'edit': can_edit,
        },
    }

    return info, status_code


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('dataverse', 'node')
def dataverse_delete_file(node_addon, auth, **kwargs):

    node = node_addon.owner
    user_settings = node_addon.user_settings

    now = datetime.datetime.utcnow()

    file_id = kwargs.get('path')
    if file_id is None:
        raise HTTPError(httplib.NOT_FOUND)

    try:
        connection = connect_from_settings_or_401(user_settings)
    except HTTPError as error:
        if error.code == httplib.UNAUTHORIZED:
            connection = None
        else:
            raise

    dataverse = get_dataverse(connection, node_addon.dataverse_alias)
    dataset = get_dataset(dataverse, node_addon.dataset_doi)
    file = get_file_by_id(dataset, file_id)

    delete_file(file)

    # Check if file was deleted
    if get_file_by_id(dataset, file_id) is not None:
        raise HTTPError(httplib.BAD_REQUEST)

    node.add_log(
        action='dataverse_file_removed',
        params={
            'project': node.parent_id,
            'node': node._primary_key,
            'filename': file.name,
            'dataset': dataset.title,
        },
        auth=auth,
        log_date=now,
    )

    return {}


@must_be_contributor_or_public
@must_have_addon('dataverse', 'node')
def dataverse_get_rendered_file(**kwargs):
    """

    """
    node_settings = kwargs['node_addon']
    file_id = kwargs['path']

    cache_file = '{0}.html'.format(file_id)
    return get_cache_content(node_settings, cache_file)


def get_file_content(file_id, token, name_only=False):
    url = 'http://{0}/api/access/datafile/{1}'.format(settings.HOST, file_id)
    params = {'key': token}
    response = requests.head(url, params=params, allow_redirects=True) \
        if name_only else requests.get(url, params=params)

    if response.status_code == http.NOT_FOUND:
        raise HTTPError(http.NOT_FOUND)

    filename = response.headers['content-disposition'].split('"')[1]

    return filename, response.content


def fail_if_unauthorized(node_addon, auth, file_id):

    node = node_addon.owner
    user_settings = node_addon.user_settings

    if file_id is None:
        raise HTTPError(httplib.NOT_FOUND)

    connection = connect_from_settings(user_settings)
    dataverse = get_dataverse(connection, node_addon.dataverse_alias)
    dataset = get_dataset(dataverse, node_addon.dataset_doi)
    published_file_ids = [f.id for f in get_files(dataset, published=True)]
    all_file_ids = [f.id for f in get_files(dataset)] + published_file_ids

    if file_id not in all_file_ids:
        raise HTTPError(httplib.FORBIDDEN)
    elif not node.can_edit(auth) and file_id not in published_file_ids:
        raise HTTPError(httplib.UNAUTHORIZED)
