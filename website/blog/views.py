import logging
import httplib
import httplib as http
import urllib as url

import post
from file_handler import FileHandler
from render import Renderer
from HTMLParser import HTMLParser

from framework.auth.decorators import collect_auth
from framework.exceptions import HTTPError, PermissionsError

from website.models import User
from website.profile import utils as profile_utils


def get_posts(profile):
    user = "pierce.tickle@gmail.com"
    password = "password"
    file_handler = FileHandler("38zmk", user, password)
    posts = file_handler.get_file_list()
    return posts['data']

def _blog_view(profile, is_profile=False):
    if profile and profile.is_disabled:
        raise HTTPError(http.GONE)
    if profile:
        profile_user_data = profile_utils.serialize_user(profile, full=True)
        return {
            'profile': profile_user_data,
            'posts': get_posts(profile)
        }


@collect_auth
def blog_view_id(uid, auth):
    user = User.load(uid)
    is_profile = auth and auth.user == user
    return _blog_view(user, is_profile)


def render_post(file):
    user = "pierce.tickle@gmail.com"
    password = "password"
    file_handler = FileHandler("38zmk", user, password)
    theme = "website/static/ghost_themes/casper"
    hbs = theme + "/post.hbs"
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


def _post_view(profile, bid, is_profile=False):
    blog_file = url.unquote(bid).decode('utf8')[:-1] + ".md"
    post = render_post(blog_file)
    if profile and profile.is_disabled:
        raise HTTPError(http.GONE)
    if profile:
        profile_user_data = profile_utils.serialize_user(profile, full=True)
        return {
            'profile': profile_user_data,
            'post': post
        }


@collect_auth
def post_view_id(uid, bid, auth):
    user = User.load(uid)
    is_profile = auth and auth.user == user
    return _post_view(user, bid, is_profile)
