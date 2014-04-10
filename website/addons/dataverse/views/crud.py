import os
import datetime
import logging
import requests
from bs4 import BeautifulSoup

from framework import request, make_response
from framework.flask import secure_filename, redirect, send_file
from framework.exceptions import HTTPError

from website.project.decorators import must_have_permission
from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon
from website.project.views.node import _view_project
from website.project.views.file import get_cache_content
from website.util import rubeus
from website.addons.dataverse.settings import HOST
from website.addons.dataverse.model import connect

import httplib as http

logger = logging.getLogger(__name__)

session = requests.Session()

@must_be_contributor_or_public
@must_have_addon('dataverse', 'node')
def dataverse_download_file(**kwargs):

    file_id = kwargs.get('path')
    if file_id is None:
        raise HTTPError(http.NOT_FOUND)

    return redirect('http://{0}/dvn/FileDownload/?fileId={1}'.format(HOST, file_id))


@must_be_contributor_or_public
@must_have_addon('dataverse', 'node')
def dataverse_download_file_proxy(**kwargs):

    file_id = kwargs.get('path')
    if file_id is None:
        raise HTTPError(http.NOT_FOUND)

    content = scrape_dataverse(file_id)

    # Build response
    resp = make_response(content)
    resp.headers['Content-Disposition'] = 'attachment; filename={0}'.format(
        file_id
    )

    resp.headers['Content-Type'] = 'application/octet-stream'

    return resp


# TODO: Remove unnecessary API calls
@must_be_contributor_or_public
@must_have_addon('dataverse', 'node')
def dataverse_view_file(**kwargs):

    auth = kwargs['auth']
    node = kwargs['node'] or kwargs['project']
    node_settings = kwargs['node_addon']

    file_id = kwargs.get('path')
    if file_id is None:
        raise HTTPError(http.NOT_FOUND)

    connection = connect(
        node_settings.dataverse_username,
        node_settings.dataverse_password
    )

    study = connection.get_dataverses()[node_settings.dataverse_number].get_study_by_hdl(node_settings.study_hdl)
    file = study.get_file_by_id(file_id)

    # Get file URL
    url = node.web_url_for('dataverse_view_file', path=file_id)

    # Get or create rendered file
    _, ext = os.path.splitext(file.name)
    cache_file = '{0}.html'.format(file_id)
    rendered = get_cache_content(node_settings, cache_file)

    if rendered is None:
        data = scrape_dataverse(file_id)
        rendered = get_cache_content(
            node_settings, cache_file, start_render=True,
            file_path=file_id + ext, file_content=data,
            download_path='{}proxy/'.format(url),
        )

    rv = {
        'file_name': file.name,
        'rendered': rendered,
        'render_url': node.api_url_for('dataverse_get_rendered_file',
                                       path=file_id),
        'download_url': node.api_url_for('dataverse_download_file',
                                         path=file_id),
    }
    rv.update(_view_project(node, auth))
    return rv


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('dataverse', 'node')
def dataverse_upload_file(**kwargs):

    node = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']
    node_settings = kwargs['node_addon']

    now = datetime.datetime.utcnow()

    can_edit = node.can_edit(auth) and not node.is_registration
    can_view = node.can_view(auth)

    connection = connect(
        node_settings.dataverse_username,
        node_settings.dataverse_password
    )

    dataverse = connection.get_dataverses()[node_settings.dataverse_number]
    study = dataverse.get_study_by_hdl(node_settings.study_hdl)

    upload = request.files.get('file')
    filename = secure_filename(upload.filename)

    # Todo: Allow renaming
    if study.get_file(filename) is not None:
        raise HTTPError(http.FORBIDDEN)

    content = upload.read()

    study.add_file_obj(filename, content)
    file_id = study.get_file(filename).id

    if file_id is not None:
        node.add_log(
            action='dataverse_file_added',
            params={
                'project': node.parent_id,
                'node': node._primary_key,
                'filename': filename,
                'path': node.web_url_for('dataverse_view_file', path=file_id),
                'dataverse': {
                    'dataverse': dataverse.title,
                    'study': study.get_title(),
                }
            },
            auth=auth,
            log_date=now,
        )

        info = {
            'addon': 'dataverse',
            'name': filename,
            'size': [
                len(content),
                rubeus.format_filesize(len(content))
            ],
            'kind': 'file',
            'urls': {
                    'view': node.web_url_for('dataverse_view_file',
                                             path=file_id),
                    'download': node.api_url_for('dataverse_download_file',
                                                 path=file_id),
                    'delete': node.api_url_for('dataverse_delete_file',
                                               path=file_id),
            },
            'permissions': {
                'view': can_view,
                'edit': can_edit,
            },
        }

        return info, 201

    raise HTTPError(http.BAD_REQUEST)


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('dataverse', 'node')
def dataverse_delete_file(**kwargs):

    node = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']
    node_settings = kwargs['node_addon']

    now = datetime.datetime.utcnow()

    file_id = kwargs.get('path')
    if file_id is None:
        raise HTTPError(http.NOT_FOUND)

    connection = connect(
        node_settings.dataverse_username,
        node_settings.dataverse_password
    )

    dataverse = connection.get_dataverses()[node_settings.dataverse_number]
    study = dataverse.get_study_by_hdl(node_settings.study_hdl)
    file = study.get_file_by_id(file_id)

    study.delete_file(file)

    # TODO: Check if file was deleted

    node.add_log(
        action='dataverse_file_removed',
        params={
            'project': node.parent_id,
            'node': node._primary_key,
            'filename': file.name,
            'dataverse': {
                'dataverse': dataverse.title,
                'study': study.get_title(),
            }
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


def scrape_dataverse(file_id):

    # Go to file url
    response = session.get('http://{0}/dvn/FileDownload/?fileId={1}'.format(HOST, file_id))

    # Agree to terms if necessary
    if '<title>Account Terms of Use -' in response.content:

        parsed = BeautifulSoup(response.content)
        view_state = parsed.find(id='javax.faces.ViewState').attrs.get('value')
        data = {
            'form1':'form1',
            'javax.faces.ViewState': view_state,
            'form1:termsAccepted':'on',
            'form1:termsButton':'Continue',
        }
        session.post('http://{0}/dvn/faces/study/TermsOfUsePage.xhtml'.format(HOST), data=data)
        response = session.get('http://{0}/dvn/FileDownload/?fileId={1}'.format(HOST, file_id))

    # return file
    return response.content