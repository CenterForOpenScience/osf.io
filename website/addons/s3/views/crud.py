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

from .utils import _page_content, get_cache_file_name
from website.addons.s3.utils import create_version_list

from website import models

from urllib import unquote

from website.addons.s3.settings import MAX_RENDER_SIZE

#TODO Anything begining with s3_ can be staged for removal
#S3 Page is also staged to be removed


@must_be_contributor_or_public
@must_have_addon('s3', 'node')
def s3_page(*args, **kwargs):
    user = kwargs['user']
    user_settings = user.get_addon('s3')

    node = kwargs['node'] or kwargs['project']

    s3 = node.get_addon('s3')
    data = _view_project(node, user, primary=True)

    rv = _page_content(str(kwargs['pid']), s3, user_settings)
    rv.update({
        'addon_page_js': s3.config.include_js['page'],
        'addon_page_css': s3.config.include_css['page'],
    })
    rv.update(s3.config.to_json())
    rv.update(data)

    return rv


@must_be_contributor_or_public
@must_have_addon('s3', 'node')
def s3_download(*args, **kwargs):
    node = kwargs['node'] or kwargs['project']
    s3 = node.get_addon('s3')

    keyName = kwargs['key']
    if keyName is None:
        raise HTTPError(http.NOT_FOUND)
    connect = S3Wrapper.from_addon(s3)
    return redirect(connect.download_file_URL(keyName.replace('&spc', ' ').replace('&sl', '/')))


@must_be_contributor
@must_have_addon('s3', 'node')
def s3_delete(*args, **kwargs):
    node = kwargs['node'] or kwargs['project']
    s3 = node.get_addon('s3')
    dfile = request.json.get('keyPath')
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


@must_be_contributor
@must_have_addon('s3', 'node')
def s3_new_folder(*args, ** kwargs):
    node = kwargs['node'] or kwargs['project']
    s3 = node.get_addon('s3')
    folderPath = request.json.get('path').replace(
        '&spc', ' ').replace('&sl', '/')

    connect = S3Wrapper.from_addon(s3)
    connect.createFolder(folderPath)
    return {}


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


#TODO Check to see if file is already rendered?
#TODO Change from MD5 to VID
@must_be_contributor_or_public
@must_have_addon('s3', 'node')
def view(*args, **kwargs):

    path = kwargs.get('path')
    vid = request.args.get('vid')
    if not path:
        raise HTTPError(http.NOT_FOUND)

    node_settings = kwargs['node_addon']
    user = kwargs['user']
    node = kwargs['node'] or kwargs['project']

    wrapper = S3Wrapper.from_addon(node_settings)
    key = wrapper.get_wrapped_key(unquote(path), vid=vid)

    # Test to see if the file size is within limit
    if key.s3Key.size > MAX_RENDER_SIZE:
        raise HTTPError(http.BAD_REQUEST)

    download_url = node.api_url + 's3/download/' + path + '/'

    file_contents = key.s3Key.get_contents_as_string()

    #TODO Change me to url (not api/v1/)
    render_url = node.url + 's3/render/' + path + '/?md5=' + key.md5

    cache_name = get_cache_file_name(path, key.md5)

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
    md5 = request.args.get('md5')

    cache_file = get_cache_file_name(path, md5)

    return get_cache_content(node_settings, cache_file)
