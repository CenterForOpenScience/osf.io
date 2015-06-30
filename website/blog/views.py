import logging
import httplib
import httplib as http
import urllib as url
import requests

import post
from file_handler import FileHandler
from render import Renderer
from HTMLParser import HTMLParser
from ghostpy._compiler import _ghostpy_

from framework.auth.decorators import collect_auth
from framework.exceptions import HTTPError, PermissionsError

from website.models import User
from website.profile import utils as profile_utils

user = 'pierce.tickle@gmail.com'
password = 'password'


def get_posts(guid):
    file_handler = FileHandler(guid, user, password)
    posts = file_handler.get_file_list()
    return posts['data']


def blog_view_pid(pid):
    return _blog_view(pid, is_profile=False)


@collect_auth
def blog_view_id(uid, auth):
    return _blog_view(uid, is_profile=True)


def _blog_view(guid, is_profile=False):
    if is_profile:
        guid = get_blog_dir(guid)
    return {
        'posts': get_posts(guid)
    }


def render_post(guid, file):
    file_handler = FileHandler(guid, user, password)
    theme = "website/static/ghost_themes/casper"
    hbs = theme + "/post.hbs"
    _ghostpy_['theme'] = theme
    _ghostpy_['base'] = "http://localhost:5000/%s/blog/" % guid
    renderer = Renderer(theme)
    posts = file_handler.get_posts(file)
    post_dict = post.parse_blog(posts)
    output = renderer.render(hbs, {'post': post_dict})
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


def _post_view(guid, bid, is_profile=False):
    _ghostpy_['context'].append('post')
    blog_file = url.unquote(bid).decode('utf8')[:-1] + ".md"
    if is_profile:
        guid = get_blog_dir(guid)
    post = render_post(guid, blog_file)
    return {
        'post': post
    }


def post_view_id(uid, bid):
    return _post_view(uid, bid, is_profile=True)


def post_view_pid(pid, bid):
    return _post_view(pid, bid, is_profile=False)


def get_blog_dir(guid):
    uri = "http://localhost:8000"
    path = "/v2/users/" + guid + "/nodes/?filter[title]=Blog"
    data_ = requests.get(uri+path, auth=(user, password)).json()['data']
    guid = filter(lambda node: node['title'] == "Blog", data_)[0].get('id')
    return guid
