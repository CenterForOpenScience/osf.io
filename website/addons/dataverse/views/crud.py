import os
import datetime
import logging
import requests
from bs4 import BeautifulSoup

from framework import request, make_response
from framework.flask import secure_filename, redirect, send_file
from framework.exceptions import HTTPError

from website.project.decorators import must_be_contributor_or_public, must_have_addon, must_not_be_registration
from website.project.views.node import _view_project
from website.project.views.file import get_cache_content
from website.util import rubeus
from website.addons.dataverse.config import HOST
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

    study = connection.get_dataverses()[int(node_settings.dataverse_number)].get_study_by_hdl(node_settings.study_hdl)
    file = study.get_file_by_id(file_id)

    # Get file URL
    url = os.path.join(node.api_url, 'dataverse', 'file', file_id) + '/'

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
        'render_url': '{0}render/'.format(url),
        'rendered': rendered,
        'download_url': '{0}proxy/'.format(url),
    }
    rv.update(_view_project(node, auth))
    return rv



@must_be_contributor_or_public
@must_not_be_registration
@must_have_addon('dataverse', 'node')
def dataverse_upload_file(**kwargs):

    node = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']
    node_settings = kwargs['node_addon']
    now = datetime.datetime.utcnow()

    path = kwargs.get('path', '')

    connection = connect(
        node_settings.dataverse_username,
        node_settings.dataverse_password
    )
    study = connection.get_dataverses()[int(node_settings.dataverse_number)].get_study_by_hdl(node_settings.study_hdl)

    upload = request.files.get('file')
    filename = secure_filename(upload.filename)

    # Todo: Allow renaming
    if study.get_file(filename) is not None:
        raise HTTPError(http.FORBIDDEN)

    content = upload.read()

    study.add_file_obj(filename, content)
    file_id = study.get_file(filename).fileId

    if file_id is not None:
        # TODO: Log for dataverse
        # node.add_log(
        #     action=(
        #         'dataverse_' + (
        #             models.NodeLog.FILE_ADDED
        #         )
        #     ),
        #     params={
        #         'project': node.parent_id,
        #         'node': node._primary_key,
        #         'path': os.path.join(path, filename),
        #     },
        #     auth=auth,
        #     log_date=now,
        # )

        url = os.path.join(node_settings.owner.api_url, 'dataverse', 'file', file_id) + '/'

        info = {
            'addon': 'dataverse',
            'name': filename,
            'size': [
                len(content),
                rubeus.format_filesize(len(content))
            ],
            'kind': 'file',
            'urls': {
                    'view': url,
                    'download': '{0}download/'.format(url),
                    'delete': url,
            },
            'permissions': {
                'view': True,
                'edit': True,
            },
        }

        return info, 201

    raise HTTPError(http.BAD_REQUEST)


@must_be_contributor_or_public
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
    study = connection.get_dataverses()[int(node_settings.dataverse_number)].get_study_by_hdl(node_settings.study_hdl)

    study.delete_file(study.get_file_by_id(file_id))

    # TODO: Logs

    # if data is None:
    #     raise HTTPError(http.BAD_REQUEST)
    #
    # node.add_log(
    #     action='dataverse_' + models.NodeLog.FILE_REMOVED,
    #     params={
    #         'project': node.parent_id,
    #         'node': node._primary_key,
    #         'path': path,
    #         'dataverse': {
    #             'user': node_settings.user,
    #             'repo': node_settings.repo,
    #         },
    #     },
    #     auth=auth,
    #     log_date=now,
    # )

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