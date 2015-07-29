import httplib
import urllib
import math

import post
from file_handler import FileHandler
from render import Renderer
from HTMLParser import HTMLParser
import ghostpy._compiler as compiler
# import compiler

from website.models import User, Node
from website.util import rubeus
from website.project.utils import serialize_node
from framework.exceptions import HTTPError, PermissionsError
from framework.auth.decorators import collect_auth
from framework.flask import redirect


def get_posts(node):
    file_handler = FileHandler(node)
    posts = file_handler.get_file_list()
    return posts


def blog_view(guid, int=None):
    if int == '1':
        return redirect("/"+guid+"/blog/")
    if int is None:
        int=1
    guid = resolve_guid(guid)
    compiler._ghostpy_ = compiler.reset()
    compiler._ghostpy_['context'].append('index')
    posts = render(guid, file=None, page=int)
    return {
        'posts': posts
    }


def post_view(guid, bid):
    guid = resolve_guid(guid)
    compiler._ghostpy_ = compiler.reset()
    compiler._ghostpy_['context'].append('post')
    blog_file = urllib.unquote(bid).decode('utf8') + ".md"
    post = render(guid, blog_file, page=None)
    return {
        'post': post
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
                    'body_class': 'post-template'}
    html = renderer.render(theme + '/default.hbs', blog_dict, default_dict)
    parser = HTMLParser()
    html = parser.unescape(html)
    return html


@collect_auth
def resolve_guid(guid, auth, permissions_needed=False):
    node = Node.load(guid)
    if node is not None:
        user = auth.user
        if user not in node.contributors and permissions_needed:
            raise PermissionsError
    else:
        user = User.load(guid)
        if auth.user != user and permissions_needed:
            raise PermissionsError
        guid = user.blog_guid
    return guid


@collect_auth
def edit_or_create_post(guid, auth, bid=None):
    node = Node.load(resolve_guid(guid))
    if bid is not None:
        fh = FileHandler(node)
        blog = fh.get_post(bid)
        blog_dict = post.parse_header(blog, node)
    else:
        blog_dict = None
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

    ret = serialize_node(node, auth, primary=True)
    if blog_dict is not None:
        name=blog_dict['file']
    else:
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
    ret['blog'] = blog_dict
    return ret

def get_pagination(page, total):
    ### prev = newer posts,  next = older posts
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
