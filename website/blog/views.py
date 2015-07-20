import urllib as url

import post
from file_handler import FileHandler
from render import Renderer
from HTMLParser import HTMLParser
import ghostpy._compiler as compiler

from framework.exceptions import HTTPError, PermissionsError

from framework.auth.decorators import collect_auth

from website.models import User, Node

import httplib
from website.project.utils import serialize_node
from website.util import rubeus
import math


def get_posts(node):
    file_handler = FileHandler(node)
    posts = file_handler.get_file_list()
    return posts


def blog_view_pid(pid, int=None):
    return _blog_view(pid, int=int, is_profile=False)


def blog_view_id(uid, int=None):
    return _blog_view(uid, int=int, is_profile=True)


def _blog_view(guid, int=None, is_profile=False):
    compiler._ghostpy_ = compiler.reset()
    compiler._ghostpy_['context'].append('index')
    if is_profile:
        guid = get_blog_dir(guid)
    posts = render(guid, file=None, page=int)
    return {
        'posts': posts
    }

def render(guid, file=None, page=None):
    node = Node.load(guid)
    theme = node.blog_theme
    blog_dict = node.blog_dict()
    renderer = Renderer(theme)
    if file is not None:
        file_handler = FileHandler(node)
        posts = file_handler.get_posts(file)
        hbs = theme + "/post.hbs"
        post_dict = post.parse_blog(posts, node)
        dict_ = {'post': post_dict}
    else:
        page = int(page)
        posts = get_posts(node)
        first = (page-1)*10
        last = (page*10)
        total = len(posts)
        if last > total:
            last = total
        hbs = theme + "/index.hbs"
        post_list = post.parse_posts(posts[first:last], node)
        dict_ = {'posts': post_list}
        blog_dict['pagination'] = get_pagination(page, total)
    compiler._ghostpy_['theme'] = theme
    compiler._ghostpy_['base'] = "http://localhost:5000/%s/blog" % guid

    output = renderer.render(hbs, blog_dict, dict_)
    default_dict = {'body': output,
                    'date': '2015-09-04',
                    'body_class': 'post-template'}
    html = renderer.render(theme + '/default.hbs', blog_dict, default_dict)
    parser = HTMLParser()
    html = parser.unescape(html)
    return html


def _post_view(guid, bid, is_profile=False):
    compiler._ghostpy_ = compiler.reset()
    compiler._ghostpy_['context'].append('post')
    blog_file = url.unquote(bid).decode('utf8') + ".md"
    if is_profile:
        guid = get_blog_dir(guid)
    post = render(guid, blog_file, page=None)
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
    user = User.load(uid)
    if auth.user != user:
        raise PermissionsError
    guid = get_blog_dir(uid)
    node = Node.load(guid)
    return create_post(node, auth)

def create_post(node, auth):
    node_addon = node.get_addon('osfstorage')

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

    return addon_view_file(auth, node)


@collect_auth
def new_project_post(auth, pid):
    node = Node.load(pid)
    user = auth.user
    if user not in node.contributors:
        raise PermissionsError
    return create_post(node, auth)

def addon_view_file(auth, node):
    ret = serialize_node(node, auth, primary=True)
    name = "blog" + str(len(get_posts(node)) + 1)
    ret.update({
        'provider': 'osfstorage',
        'urls': {
            'files': node.web_url_for('collect_file_trees'),
        },
    })
    ret.update(rubeus.collect_addon_assets(node))
    ret['name'] = name
    ret['path'] = node.blog['path']
    return ret

def get_pagination(page, total):
    #prev = newer posts
    #next = older posts
    prev = int(page) - 1
    next = int(page) + 1
    limit = 10
    pages = int(math.ceil(float(total)/limit))
    dict_ = {
        'page': page,
        'pages': pages,
        'limit': limit,
        'total': total
    }
    if prev > 0:
        dict_['prev'] = prev
    if next <= pages:
        dict_['next'] = next
    return dict_
