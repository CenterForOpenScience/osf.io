# -*- coding: utf-8 -*-

import os  # noqa
import datetime
import logging
import requests
from bs4 import BeautifulSoup
from flask import request, make_response

from framework.flask import redirect
from framework.exceptions import HTTPError
from framework.utils import secure_filename
from framework.auth.utils import privacy_info_handle
from website.addons.dataverse.client import delete_file, upload_file, \
    get_file, get_file_by_id, release_study, get_study, get_dataverse, \
    connect_from_settings_or_403, get_files

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

import httplib as http

logger = logging.getLogger(__name__)

session = requests.Session()


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('dataverse', 'node')
def dataverse_release_study(node_addon, auth, **kwargs):

    node = node_addon.owner
    user_settings = node_addon.user_settings

    now = datetime.datetime.utcnow()

    try:
        connection = connect_from_settings_or_403(user_settings)
    except HTTPError as error:
        if error.code == 403:
            connection = None
        else:
            raise

    dataverse = get_dataverse(connection, node_addon.dataverse_alias)
    study = get_study(dataverse, node_addon.study_hdl)

    if study.get_state() == 'RELEASED':
        raise HTTPError(http.CONFLICT)

    release_study(study)

    # Add a log
    node.add_log(
        action='dataverse_study_released',
        params={
            'project': node.parent_id,
            'node': node._primary_key,
            'study': study.title,
        },
        auth=auth,
        log_date=now,
    )

    return {'study': study.title}, http.OK


@must_be_contributor_or_public
@must_have_addon('dataverse', 'node')
def dataverse_download_file(node_addon, auth, **kwargs):

    file_id = kwargs.get('path')

    fail_if_unauthorized(node_addon, auth, file_id)
    fail_if_private(file_id)

    url = 'http://{0}/dvn/FileDownload/?fileId={1}'.format(HOST, file_id)
    return redirect(url)


@must_be_contributor_or_public
@must_have_addon('dataverse', 'node')
def dataverse_download_file_proxy(node_addon, auth, **kwargs):

    file_id = kwargs.get('path')

    fail_if_unauthorized(node_addon, auth, file_id)
    fail_if_private(file_id)

    filename, content = scrape_dataverse(file_id)

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
    file_id = kwargs.get('path')

    fail_if_unauthorized(node_addon, auth, file_id)
    fail_if_private(file_id)

    anonymous = has_anonymous_link(node, auth)

    download_url = node.web_url_for('dataverse_download_file', path=file_id)
    dataverse_url = 'http://{0}/dvn/dv/'.format(HOST) + node_addon.dataverse_alias
    study_url = 'http://dx.doi.org/' + node_addon.study_hdl
    delete_url = node.api_url_for('dataverse_delete_file', path=file_id)

    data = {
        'node': {
            'id': node._id,
            'title': node.title
        },
        'filename': scrape_dataverse(file_id, name_only=True)[0],
        'dataverse': privacy_info_handle(node_addon.dataverse, anonymous),
        'study': privacy_info_handle(node_addon.study, anonymous),
        'urls': {
            'dataverse': privacy_info_handle(dataverse_url, anonymous),
            'study': privacy_info_handle(study_url, anonymous),
            'download': privacy_info_handle(download_url, anonymous),
            'delete': privacy_info_handle(delete_url, anonymous),
            'files': node.web_url_for('collect_file_trees'),
        }
    }

    return {
        'data': data,
    }, http.OK


@must_be_contributor_or_public
@must_have_addon('dataverse', 'node')
def dataverse_view_file(node_addon, auth, **kwargs):

    node = node_addon.owner

    file_id = kwargs.get('path')

    fail_if_unauthorized(node_addon, auth, file_id)
    fail_if_private(file_id)

    # lazily create a file GUID record
    file_obj, created = DataverseFile.get_or_create(node=node, path=file_id)

    redirect_url = check_file_guid(file_obj)
    if redirect_url:
        return redirect(redirect_url)

    # Get or create rendered file
    cache_file_name = '{0}.html'.format(file_id)
    rendered = get_cache_content(node_addon, cache_file_name)

    if rendered is None:
        filename, content = scrape_dataverse(file_id)
        download_url = node.api_url_for(
            'dataverse_download_file_proxy', path=file_id
        )
        rendered = get_cache_content(
            node_addon,
            cache_file_name,
            start_render=True,
            remote_path=file_obj.file_id,
            file_content=content,
            download_url=download_url,
        )
    else:
        filename, _ = scrape_dataverse(file_id, name_only=True)

    rv = {
        'file_name': filename,
        'rendered': rendered,
        'urls': {
            'render': node.api_url_for('dataverse_get_rendered_file',
                                       path=file_id),
            'download': node.web_url_for('dataverse_download_file',
                                         path=file_id),
            'info': node.api_url_for('dataverse_get_file_info',
                                     path=file_id),
        }

    }
    rv.update(_view_project(node, auth))
    return rv


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('dataverse', 'node')
def dataverse_upload_file(node_addon, auth, **kwargs):

    node = node_addon.owner
    user_settings = node_addon.user_settings

    now = datetime.datetime.utcnow()

    can_edit = node.can_edit(auth) and not node.is_registration
    can_view = node.can_view(auth)

    try:
        connection = connect_from_settings_or_403(user_settings)
    except HTTPError as error:
        if error.code == 403:
            connection = None
        else:
            raise

    dataverse = get_dataverse(connection, node_addon.dataverse_alias)
    study = get_study(dataverse, node_addon.study_hdl)

    upload = request.files.get('file')
    filename = secure_filename(upload.filename)
    action = 'file_uploaded'
    old_id = None

    # Fail if file is too small (Dataverse issue)
    content = upload.read()
    if len(content) < 5:
        raise HTTPError(http.UNSUPPORTED_MEDIA_TYPE)

    # Replace file if old version exists
    old_file = get_file(study, filename)
    if old_file is not None:
        action = 'file_updated'
        old_id = old_file.id
        delete_file(old_file)
        # Check if file was deleted
        if get_file_by_id(study, old_id) is not None:
            raise HTTPError(http.BAD_REQUEST)

    upload_file(study, filename, content)
    file = get_file(study, filename)

    if file is None:
        raise HTTPError(http.BAD_REQUEST)

    node.add_log(
        action='dataverse_file_added',
        params={
            'project': node.parent_id,
            'node': node._primary_key,
            'filename': filename,
            'path': node.web_url_for('dataverse_view_file', path=file.id),
            'study': study.title,
        },
        auth=auth,
        log_date=now,
    )

    info = {
        'addon': 'dataverse',
        'file_id': file.id,
        'old_id': old_id,
        'name': filename,
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
        'actionTaken': action,
    }

    return info, 201


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('dataverse', 'node')
def dataverse_delete_file(node_addon, auth, **kwargs):

    node = node_addon.owner
    user_settings = node_addon.user_settings

    now = datetime.datetime.utcnow()

    file_id = kwargs.get('path')
    if file_id is None:
        raise HTTPError(http.NOT_FOUND)

    try:
        connection = connect_from_settings_or_403(user_settings)
    except HTTPError as error:
        if error.code == 403:
            connection = None
        else:
            raise

    dataverse = get_dataverse(connection, node_addon.dataverse_alias)
    study = get_study(dataverse, node_addon.study_hdl)
    file = get_file_by_id(study, file_id)

    delete_file(file)

    # Check if file was deleted
    if get_file_by_id(study, file_id) is not None:
        raise HTTPError(http.BAD_REQUEST)

    node.add_log(
        action='dataverse_file_removed',
        params={
            'project': node.parent_id,
            'node': node._primary_key,
            'filename': file.name,
            'study': study.title,
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


def scrape_dataverse(file_id, name_only=False):

    # Go to file url
    url = 'http://{0}/dvn/FileDownload/?fileId={1}'.format(HOST, file_id)
    response = session.head(url, allow_redirects=True) if name_only else session.get(url)

    # Agree to terms if a redirect has occurred
    if response.history:
        response = session.get(url) if name_only else response
        parsed = BeautifulSoup(response.content)
        view_state = parsed.find(id='javax.faces.ViewState').attrs.get('value')
        data = {
            'form1': 'form1',
            'javax.faces.ViewState': view_state,
            'form1:termsAccepted': 'on',
            'form1:termsButton': 'Continue',
        }
        terms_url = 'http://{0}/dvn/faces/study/TermsOfUsePage.xhtml'.format(HOST)
        session.post(terms_url, data=data)
        response = session.head(url) if name_only else session.get(url)

    if 'content-disposition' not in response.headers.keys():
        raise HTTPError(http.NOT_FOUND)

    filename = response.headers['content-disposition'].split('"')[1]

    return filename, response.content


def fail_if_unauthorized(node_addon, auth, file_id):

    node = node_addon.owner
    user_settings = node_addon.user_settings

    if file_id is None:
        raise HTTPError(http.NOT_FOUND)

    try:
        connection = connect_from_settings_or_403(user_settings)
    except HTTPError as error:
        if error.code == 403:
            connection = None
        else:
            raise

    dataverse = get_dataverse(connection, node_addon.dataverse_alias)
    study = get_study(dataverse, node_addon.study_hdl)
    released_file_ids = [f.id for f in get_files(study, released=True)]
    all_file_ids = [f.id for f in get_files(study)] + released_file_ids

    if file_id not in all_file_ids:
        raise HTTPError(http.FORBIDDEN)
    elif not node.can_edit(auth) and file_id not in released_file_ids:
        raise HTTPError(http.UNAUTHORIZED)


def fail_if_private(file_id):

    url = 'http://{0}/dvn/FileDownload/?fileId={1}'.format(HOST, file_id)
    resp = requests.head(url)

    if resp.status_code == 403:
        raise HTTPError(
            http.FORBIDDEN,
            data={
                'message_short': 'Cannot access file contents',
                'message_long':
                    'The dataverse does not allow users to download files on ' +
                    'private studies at this time. Please contact the owner ' +
                    'of this Dataverse study for access to this file.',
            }
        )
