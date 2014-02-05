import httplib as http

import datetime

from framework import request, redirect
from framework.exceptions import HTTPError

from website.project.decorators import must_be_contributor
from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon
from website.project.views.node import _view_project
from website.project.views.file import get_cache_content

from website.addons.s3.api import S3Wrapper

from .utils import get_cache_file_name
from website.addons.s3.utils import create_version_list

from website import models

from urllib import unquote

from website.addons.s3.settings import MAX_RENDER_SIZE


@must_be_contributor_or_public
@must_have_addon('s3', 'node')
def download(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    s3 = node.get_addon('s3')
    keyName = unquote(kwargs['path'])
    vid = request.args.get('vid')

    if keyName is None:
        raise HTTPError(http.NOT_FOUND)
    connect = S3Wrapper.from_addon(s3)
    return redirect(connect.download_file_URL(keyName, vid))


@must_be_contributor
@must_have_addon('s3', 'node')
def delete(*args, **kwargs):
    node = kwargs['node'] or kwargs['project']
    s3 = node.get_addon('s3')
    dfile = unquote(kwargs['path'])

    connect = S3Wrapper.from_addon(s3)
    connect.delete_file(dfile)

    node.add_log(
        action='s3_' + models.NodeLog.FILE_REMOVED,
        params={
            'project': node.parent_id,
            'node': node._primary_key,
            'bucket': s3.bucket,
            'path': dfile,
        },
        user=kwargs['user'],
        api_key=None,
        log_date=datetime.datetime.utcnow(),
    )
    return {}


@must_be_contributor_or_public
@must_have_addon('s3', 'node')
def view(*args, **kwargs):

    path = kwargs.get('path')
    vid = request.args.get('vid')
    if not path:
        raise HTTPError(http.NOT_FOUND)

    if vid == 'Pre-versioning':
        vid = 'null'

    node_settings = kwargs['node_addon']
    user = kwargs['user']
    node = kwargs['node'] or kwargs['project']

    wrapper = S3Wrapper.from_addon(node_settings)
    key = wrapper.get_wrapped_key(unquote(path), vid=vid)

    # Test to see if the file size is within limit
    # TODO make a pretty File too large error


    cache_name = get_cache_file_name(path, key.etag)
    download_url = node.api_url + 's3/download/' + path + '/'
    render_url = node.api_url + 's3/render/' + path + '/?etag=' + key.etag

    if key.s3Key.size > MAX_RENDER_SIZE:
        render = 'File too large to render; download file to view it'
    else:
        # Check to see if the file has already been rendered.
        render = get_cache_content(node_settings, cache_name)
        if render is None:
            file_contents = key.s3Key.get_contents_as_string()
            render = get_cache_content(node_settings, cache_name, start_render=True,
                                       file_content=file_contents, download_path=download_url, file_path=path)

    versions = create_version_list(wrapper, unquote(path), node.api_url)

    rv = {
        'file_name': key.name,
        'rendered': render,
        'download_url': download_url,
        'render_url': render_url,
        'versions': versions,
        'current': key.version_id,
    }
    rv.update(_view_project(node, user, primary=True))

    return rv


@must_be_contributor_or_public
@must_have_addon('s3', 'node')
def ping_render(*args, **kwargs):
    node_settings = kwargs['node_addon']
    path = kwargs.get('path')
    etag = request.args.get('etag')

    cache_file = get_cache_file_name(path, etag)

    return get_cache_content(node_settings, cache_file)
