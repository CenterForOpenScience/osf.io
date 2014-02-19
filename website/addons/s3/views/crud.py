import httplib as http

import datetime

from framework import request, redirect, Q
from framework.exceptions import HTTPError

from website.project.decorators import must_be_contributor
from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon
from website.project.views.node import _view_project
from website.project.views.file import get_cache_content

from ..model import S3GuidFile
from website.addons.base.views import check_file_guid

from ..api import S3Wrapper

# TODO: Rename at least one utils module; could be confusing later on
from .utils import get_cache_file_name, generate_signed_url
from ..utils import create_version_list

from website import models

from urllib import unquote, quote_plus

from website.addons.s3.settings import MAX_RENDER_SIZE


@must_be_contributor_or_public
@must_have_addon('s3', 'node')
def s3_download(**kwargs):

    node = kwargs['node'] or kwargs['project']
    node_settings = kwargs['node_addon']
    key_name = unquote(kwargs['path'])
    vid = request.args.get('vid')

    if key_name is None:
        raise HTTPError(http.NOT_FOUND)
    connect = S3Wrapper.from_addon(node_settings)
    if not connect.does_key_exist(key_name):
        raise HTTPError(http.NOT_FOUND)
    return redirect(connect.download_file_URL(key_name, vid))


@must_be_contributor
@must_have_addon('s3', 'node')
def s3_delete(**kwargs):

    node = kwargs['node'] or kwargs['project']
    node_settings = kwargs['node_addon']
    dfile = unquote(kwargs['path'])

    connect = S3Wrapper.from_addon(node_settings)
    connect.delete_file(dfile)

    node.add_log(
        action='s3_' + models.NodeLog.FILE_REMOVED,
        params={
            'project': node.parent_id,
            'node': node._primary_key,
            'bucket': node_settings.bucket,
            'path': dfile,
        },
        auth=kwargs['auth'],
        log_date=datetime.datetime.utcnow(),
    )
    return {}


@must_be_contributor_or_public
@must_have_addon('s3', 'node')
def s3_view(**kwargs):

    path = kwargs.get('path')
    vid = request.args.get('vid')
    if not path:
        raise HTTPError(http.NOT_FOUND)

    if vid == 'Pre-versioning':
        vid = 'null'

    node_settings = kwargs['node_addon']
    auth = kwargs['auth']
    node = kwargs['node'] or kwargs['project']

    wrapper = S3Wrapper.from_addon(node_settings)
    key = wrapper.get_wrapped_key(unquote(path), vid=vid)

    if key is None:
        raise HTTPError(http.NOT_FOUND)

    try:
        guid = S3GuidFile.find_one(
            Q('node', 'eq', node) &
            Q('path', 'eq', path)
        )
    except:
        guid = S3GuidFile(
            node=node,
            path=path,
        )
        guid.save()

    redirect_url = check_file_guid(guid)
    if redirect_url:
        return redirect(redirect_url)

    cache_name = get_cache_file_name(path, key.etag)
    download_url = node.api_url + 's3/' + path + '/download/'
    render_url = node.api_url + 's3/' + path + '/render/?etag=' + key.etag

    if key.s3Key.size > MAX_RENDER_SIZE:
        render = 'File too large to render; download file to view it'
    else:
        # Check to see if the file has already been rendered.
        render = get_cache_content(node_settings, cache_name)
        if render is None:
            file_contents = key.s3Key.get_contents_as_string()
            render = get_cache_content(
                node_settings, cache_name, start_render=True,
                file_content=file_contents, download_path=download_url,
                file_path=path,
            )

    versions = create_version_list(wrapper, unquote(path), node.api_url)

    rv = {
        'file_name': key.name,
        'rendered': render,
        'download_url': download_url,
        'render_url': render_url,
        'versions': versions,
        'current': key.version_id,
    }
    rv.update(_view_project(node, auth, primary=True))

    return rv


@must_be_contributor_or_public
@must_have_addon('s3', 'node')
def ping_render(**kwargs):
    node_settings = kwargs['node_addon']
    path = kwargs.get('path')
    etag = request.args.get('etag')

    cache_file = get_cache_file_name(path, etag)

    return get_cache_content(node_settings, cache_file)


@must_be_contributor
@must_have_addon('s3', 'node')
def s3_upload(**kwargs):

    node = kwargs['node'] or kwargs['project']
    s3 = kwargs['node_addon']

    file_name = quote_plus(request.json.get('name'))
    mime = request.json.get('type') or 'application/octet-stream'

    update = S3Wrapper.from_addon(s3).does_key_exist(file_name)
    node.add_log(
        action='s3_' + (models.NodeLog.FILE_UPDATED if update else models.NodeLog.FILE_ADDED),
        params={
            'project': node.parent_id,
            'node': node._primary_key,
            'bucket': s3.bucket,
            'path': file_name,
            'urls': {
                'view': node.url + 's3/' + file_name + '/',
                'download': node.url + 's3/' + file_name + '/download/',
            },
        },
        auth=kwargs['auth'],
        log_date=datetime.datetime.utcnow(),
    )

    return generate_signed_url(mime, file_name, s3)
