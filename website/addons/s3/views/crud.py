import httplib as http

from framework import request
from framework.exceptions import HTTPError

from website.project.decorators import must_be_contributor
from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon
from website.project.views.node import _view_project

from website.addons.s3.api import S3Wrapper
from website.addons.s3.api import remove_user

from .utils import _page_content


@must_be_contributor
@must_have_addon('s3', 'node')
def s3_delete_access_key(*args, **kwargs):
    user = kwargs['user']

    s3_node = kwargs['node_addon']
    s3_user = user.get_addon('s3')

    # delete user from amazons data base
    # boto giveth and boto taketh away
    remove_user(s3_user.access_key, s3_user.secret_key,
                s3_node.s3_bucket, s3_node.s3_node_access_key)

    # delete our access and secret key
    s3_node.s3_node_access_key = ''
    s3_node.s3_node_secret_key = ''
    s3_node.node_auth = 0
    s3_node.save()


@must_be_contributor
@must_have_addon('s3', 'user')
def s3_remove_user_settings(*args, **kwargs):
    user = kwargs['user']
    user_settings = user.get_addon('s3')

    user_settings.access_key = ''
    user_settings.secret_key = ''
    user_settings.user_has_auth = False
    user_settings.save()
    return True


@must_be_contributor_or_public
@must_have_addon('s3', 'node')
def s3_page(*args, **kwargs):

    user = kwargs['user']
    if not user:
        return {}
    node = kwargs['node'] or kwargs['project']

    s3 = node.get_addon('s3')

    data = _view_project(node, user, primary=True)

    rv = _page_content(str(kwargs['pid']), s3)
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
    return {}


@must_be_contributor
@must_have_addon('s3', 'node')
def render_file(*args, **kwargs):
    user = kwargs['user']
    node = kwargs['node'] or kwargs['project']
    keyName = kwargs['key']

    s3 = node.get_addon('s3')

    rv = _view_project(node, user)

    rv.update({
        'addon_page_js': 'null',
        'addon_page_css': 'null',
        'complete': 1,
        'filename': keyName.replace('&spc', ' ').replace('&sl', '/')
    })

    rv.update(s3.config.to_json())
    return rv


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
