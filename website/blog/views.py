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

import httplib
from website.project.utils import serialize_node
from website.util import rubeus


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

    return addon_view_file(auth, node, uid)


def addon_view_file(auth, node, uid):
    ret = serialize_node(node, auth, primary=True)
    guid = get_blog_dir(uid)
    name = "blog" + str(len(get_posts(guid)) + 1)
    ret.update({
        'provider': 'osfstorage',
        'urls': {
            'files': node.web_url_for('collect_file_trees'),
        },
    })
    ret.update(rubeus.collect_addon_assets(node))
    ret['name'] = name
    return ret
