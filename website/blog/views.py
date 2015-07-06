import urllib as url

import post
from file_handler import FileHandler
from render import Renderer
from HTMLParser import HTMLParser
from ghostpy._compiler import _ghostpy_

from framework.auth.decorators import collect_auth
from mako.template import Template

from website.models import User


def get_posts(guid):
    file_handler = FileHandler(guid)
    posts = file_handler.get_file_list()
    return posts['data']


def blog_view_pid(pid):
    return _blog_view(pid, is_profile=False)


def blog_view_id(uid):
    return _blog_view(uid, is_profile=True)


def _blog_view(guid, is_profile=False):
    _ghostpy_['context'].append('index')
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
    _ghostpy_['theme'] = theme
    _ghostpy_['base'] = "http://localhost:5000/%s/blog" % guid
    posts = get_posts(guid)
    post_list = post.parse_posts(posts, guid)
    blog_dict = user_.blog_dict()
    output = renderer.render(hbs, blog_dict, {'posts': post_list})
    default_dict = {'body': output,
                    'date': '2015-09-04',
                    'body_class': 'post-template'}
    html = renderer.render(theme + '/default.hbs', default_dict)
    parser = HTMLParser()
    html = parser.unescape(html)
    # html_file = open("post.html", "w")
    # html_file.write(html.encode('utf-8'))
    # html_file.close()
    return html


def render_post(guid, file, uid=None):
    user_ = User.load(uid)
    theme = user_.blog_theme
    renderer = Renderer(theme)
    file_handler = FileHandler(guid)
    hbs = theme + "/post.hbs"
    _ghostpy_['theme'] = theme
    _ghostpy_['base'] = "http://localhost:5000/%s/blog" % guid
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

    # html_file = open("post.html", "w")
    # html_file.write(html.encode('utf-8'))
    # html_file.close()
    image = user_.gravatar_url
    context = {
        'image': image
    }
    return mako.render(**context)


def _post_view(guid, bid, is_profile=False):
    _ghostpy_['context'].append('post')
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
