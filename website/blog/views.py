import urllib as url

import post
from file_handler import FileHandler
from render import Renderer
from HTMLParser import HTMLParser
import ghostpy._compiler as compiler

from framework.exceptions import HTTPError, PermissionsError

from framework.auth.decorators import collect_auth
from mako.template import Template

from website.models import User, Node

from website.project.model import has_anonymous_link
from flask import request
from website.profile.utils import get_gravatar
from website.project.views.node import _view_project
from website.project.decorators import must_be_valid_project, must_be_contributor_or_public
import httplib
import furl
from flask import redirect
from flask import make_response
from website.project.utils import serialize_node
from website import settings
from website.addons.base import exceptions
import json
import uuid
from website.util import rubeus
import os

from datetime import date



def get_posts(guid):
    file_handler = FileHandler(guid)
    posts = file_handler.get_file_list()
    return posts['data']


def blog_view_pid(pid):
    return _blog_view(pid, is_profile=False)


def blog_view_id(uid):
    return _blog_view(uid, is_profile=True)


def _blog_view(guid, is_profile=False):
    compiler._ghostpy_ = compiler.reset()
    compiler._ghostpy_['context'].append('index')
    if is_profile:
        uid = guid
        guid = get_blog_dir(guid)
    posts = render_index(guid, uid)
    return {
        'posts': posts
    }


def render_index(guid, uid):
    user_ = User.load(uid)
    theme = user_.blog_theme
    renderer = Renderer(theme)
    hbs = theme + "/index.hbs"
    compiler._ghostpy_['theme'] = theme
    compiler._ghostpy_['base'] = "http://localhost:5000/%s/blog" % guid
    posts = get_posts(guid)
    post_list = post.parse_posts(posts, guid)
    blog_dict = user_.blog_dict()
    output = renderer.render(hbs, blog_dict, {'posts': post_list})
    default_dict = {'body': output,
                    'date': '2015-09-04',
                    'body_class': 'post-template'}
    html = renderer.render(theme + '/default.hbs', blog_dict, default_dict)
    parser = HTMLParser()
    html = parser.unescape(html)
    return html


def render_post(guid, file, uid=None):
    user_ = User.load(uid)
    theme = user_.blog_theme
    renderer = Renderer(theme)
    file_handler = FileHandler(guid)
    hbs = theme + "/post.hbs"
    compiler._ghostpy_['theme'] = theme
    compiler._ghostpy_['base'] = "http://localhost:5000/%s/blog" % guid
    posts = file_handler.get_posts(file)
    post_dict = post.parse_blog(posts, guid)
    blog_dict = user_.blog_dict()
    output = renderer.render(hbs, blog_dict, {'post': post_dict})
    default_dict = {'body': output,
                    'date': '2015-09-04',
                    'body_class': 'post-template'}
    mako = renderer.render(theme + '/default.hbs', default_dict)
    parser = HTMLParser()
    mako = Template(parser.unescape(mako))
    image = user_.gravatar_url
    context = {
        'image': image
    }
    return mako.render(**context)


def _post_view(guid, bid, is_profile=False):
    compiler._ghostpy_ = compiler.reset()
    compiler._ghostpy_['context'].append('post')
    blog_file = url.unquote(bid).decode('utf8') + ".md"
    uid = None
    if is_profile:
        uid = guid
        guid = get_blog_dir(guid)
    post = render_post(guid, blog_file, uid=uid)
    return {
        'post': post
    }


def post_view_id(uid, bid):
    return _post_view(uid, bid, is_profile=True)


def post_view_pid(pid, bid):
    return _post_view(pid, bid, is_profile=False)


def get_blog_dir(guid):
    user = User.load(guid)
    return user.blog_guid


@collect_auth
def new_post(auth, uid):
    guid = get_blog_dir(uid)
    extras = request.args.to_dict()
    action = extras.get('action', 'view')
    node = Node.load(guid)

    node_addon = node.get_addon('osfstorage')

    if not uid:
        raise HTTPError(httplib.BAD_REQUEST)

    if not node_addon:
        raise HTTPError(httplib.BAD_REQUEST, {
            'message_short': 'Bad Request',
            'message_long': 'The add-on containing this file is no longer connected to the {}.'.format(node.project_or_component)
        })

    if not node_addon.has_auth:
        raise HTTPError(httplib.UNAUTHORIZED, {
            'message_short': 'Unauthorized',
            'message_long': 'The add-on containing this file is no longer authorized.'
        })

    if not node_addon.complete:
        raise HTTPError(httplib.BAD_REQUEST, {
            'message_short': 'Bad Request',
            'message_long': 'The add-on containing this file is no longer configured.'
        })

    # if not path.startswith('/'):
    #     path = '/' + path

    # guid_file, created = node_addon.find_or_create_file_guid("blog" + str(len(get_posts(guid)) + 1) + ".md")
    file_name = "blog" + str(len(get_posts(guid)) + 1) + ".md"

    # if guid_file.guid_url != request.path:
    #     guid_url = furl.furl(guid_file.guid_url)
    #     guid_url.args.update(extras)
    #     return redirect(guid_url)

    # guid_file.maybe_set_version(**extras)
    #
    # if request.method == 'HEAD':
    #     download_url = furl.furl(guid_file.download_url)
    #     download_url.args.update(extras)
    #     download_url.args['accept_url'] = 'false'
    #     return make_response(('', 200, {'Location': download_url.url}))
    #
    # if action == 'download':
    #     download_url = furl.furl(guid_file.download_url)
    #     download_url.args.update(extras)
    #
    #     return redirect(download_url.url)

    # return addon_view_file(auth, node, node_addon, guid_file, extras)
    return addon_view_file(auth, node, node_addon, file_name, extras)


# def addon_view_file(auth, node, node_addon, guid_file, extras):
def addon_view_file(auth, node, node_addon, file_name, extras):
    # TODO: resolve circular import issue
    from website.addons.wiki import settings as wiki_settings

    ret = serialize_node(node, auth, primary=True)

    # Disable OSF Storage file deletion in DISK_SAVING_MODE
    if settings.DISK_SAVING_MODE and node_addon.config.short_name == 'osfstorage':
        ret['user']['can_edit'] = False
    #
    # try:
    #     guid_file.enrich()
    # except exceptions.AddonEnrichmentError as e:
    #     error = e.as_html()
    # else:
    #     error = None

    error = None

    # if guid_file._id not in node.file_guid_to_share_uuids:
    #     node.file_guid_to_share_uuids[guid_file._id] = uuid.uuid4()
    #     node.save()
    #
    # if ret['user']['can_edit']:
    #     sharejs_uuid = str(node.file_guid_to_share_uuids[guid_file._id])
    # else:
    #     sharejs_uuid = None
    #
    # size = getattr(guid_file, 'size', None)
    # if size is None:  # Size could be 0 which is a falsey value
    #     size = 9966699  # if we dont know the size assume its to big to edit

    ret.update({
        # 'error': error.replace('\n', '') if error else None,
        'provider': 'osfstorage',
        # 'file_path': guid_file.waterbutler_path,
        # 'panels_used': ['edit', 'view'],
        # 'sharejs_uuid': sharejs_uuid,
        'urls': {
            'files': node.web_url_for('collect_file_trees'),
        #     'render': guid_file.mfr_render_url,
        #     'sharejs': wiki_settings.SHAREJS_URL,
        #     'mfr': settings.MFR_SERVER_URL,
        #     'gravatar': get_gravatar(auth.user, 25),
        },
        # # Note: must be called after get_or_start_render. This is really only for github
        # 'size': size,
        # 'extra': json.dumps(getattr(guid_file, 'extra', {})),
        # #NOTE: get_or_start_render must be called first to populate name
        # 'file_name': getattr(guid_file, 'name', os.path.split(guid_file.waterbutler_path)[1]),
        # 'materialized_path': getattr(guid_file, 'materialized', guid_file.waterbutler_path),
        'file_name': file_name
    })

    ret.update(rubeus.collect_addon_assets(node))
    return ret


def save_post(uid):
    header_start = "/**\n"
    date_ = "date: " + str(date.today()) + "\n"
    author = "author: " + uid + "\n"
    header_end = "**/\n"
    content = request.form['content']
    text = header_start + date_ + author + header_end + content
