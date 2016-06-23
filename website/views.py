# -*- coding: utf-8 -*-
import itertools
import httplib as http
import logging
import math
import urllib

from modularodm import Q
from modularodm.exceptions import NoResultsFound
from flask import request

from framework import utils, sentry
from framework.auth.core import User
from framework.auth.decorators import must_be_logged_in
from framework.auth.forms import SignInForm, ResetPasswordForm, ForgotPasswordForm
from framework.exceptions import HTTPError
from framework.flask import redirect  # VOL-aware redirect
from framework.forms import utils as form_utils
from framework.routing import proxy_url
from website.institutions.views import view_institution
from framework.auth.forms import RegistrationForm
from framework.auth.forms import ForgotPasswordForm
from framework.auth.decorators import must_be_logged_in

from website.models import Guid
from website.models import Node, Institution
from website.project import model
from website.project import new_bookmark_collection
from website.util import sanitize, permissions

logger = logging.getLogger(__name__)


def _render_node(node, auth=None):
    """

    :param node:
    :return:

    """
    perm = None
    # NOTE: auth.user may be None if viewing public project while not
    # logged in
    if auth and auth.user and node.get_permissions(auth.user):
        perm_list = node.get_permissions(auth.user)
        perm = permissions.reduce_permissions(perm_list)

    return {
        'title': node.title,
        'id': node._primary_key,
        'url': node.url,
        'api_url': node.api_url,
        'primary': node.primary,
        'date_modified': utils.iso8601format(node.date_modified),
        'category': node.category,
        'permissions': perm,  # A string, e.g. 'admin', or None,
        'archiving': node.archiving,
    }


def _render_nodes(nodes, auth=None, show_path=False):
    """

    :param nodes:
    :return:
    """
    ret = {
        'nodes': [
            _render_node(node, auth)
            for node in nodes
        ],
        'show_path': show_path
    }
    return ret


def index():
    try:
        #TODO : make this way more robust
        inst = Institution.find_one(Q('domains', 'eq', request.host.lower()))
        inst_dict = view_institution(inst._id)
        inst_dict.update({
            'home': False,
            'institution': True,
            'redirect_url': '/institutions/{}/'.format(inst._id)
        })
        return inst_dict
    except NoResultsFound:
        pass
    return {'home': True}


def find_bookmark_collection(user):
    bookmark_collection = Node.find(Q('is_bookmark_collection', 'eq', True) & Q('contributors', 'eq', user._id))
    if bookmark_collection.count() == 0:
        new_bookmark_collection(user)
    return bookmark_collection[0]


@must_be_logged_in
def dashboard(auth):
    return redirect('/')


@must_be_logged_in
def my_projects(auth):
    user = auth.user
    bookmark_collection = find_bookmark_collection(user)
    my_projects_id = bookmark_collection._id
    return {'addons_enabled': user.get_addon_names(),
            'dashboard_id': my_projects_id,
            }


def validate_page_num(page, pages):
    if page < 0 or (pages and page >= pages):
        raise HTTPError(http.BAD_REQUEST, data=dict(
            message_long='Invalid value for "page".'
        ))


def paginate(items, total, page, size):
    pages = math.ceil(total / float(size))
    validate_page_num(page, pages)

    start = page * size
    paginated_items = itertools.islice(items, start, start + size)

    return paginated_items, pages


@must_be_logged_in
def watched_logs_get(**kwargs):
    user = kwargs['auth'].user
    try:
        page = int(request.args.get('page', 0))
    except ValueError:
        raise HTTPError(http.BAD_REQUEST, data=dict(
            message_long='Invalid value for "page".'
        ))
    try:
        size = int(request.args.get('size', 10))
    except ValueError:
        raise HTTPError(http.BAD_REQUEST, data=dict(
            message_long='Invalid value for "size".'
        ))

    total = sum(1 for x in user.get_recent_log_ids())
    paginated_logs, pages = paginate(user.get_recent_log_ids(), total, page, size)
    logs = (model.NodeLog.load(id) for id in paginated_logs)

    return {
        'logs': [serialize_log(log) for log in logs],
        'total': total,
        'pages': pages,
        'page': page
    }


def serialize_log(node_log, auth=None, anonymous=False):
    '''Return a dictionary representation of the log.'''
    return {
        'id': str(node_log._primary_key),
        'user': node_log.user.serialize()
        if isinstance(node_log.user, User)
        else {'fullname': node_log.foreign_user},
        'contributors': [node_log._render_log_contributor(c) for c in node_log.params.get('contributors', [])],
        'action': node_log.action,
        'params': sanitize.unescape_entities(node_log.params),
        'date': utils.iso8601format(node_log.date),
        'node': node_log.original_node.serialize(auth) if node_log.original_node else None,
        'anonymous': anonymous
    }


def reproducibility():
    return redirect('/ezcuj/wiki')


def signin_form():
    return form_utils.jsonify(SignInForm())


def forgot_password_form():
    return form_utils.jsonify(ForgotPasswordForm(prefix='forgot_password'))


def reset_password_form():
    return form_utils.jsonify(ResetPasswordForm())


# GUID ###

def _build_guid_url(base, suffix=None):
    url = '/'.join([
        each.strip('/') for each in [base, suffix]
        if each
    ])
    if not isinstance(url, unicode):
        url = url.decode('utf-8')
    return u'/{0}/'.format(url)


def resolve_guid(guid, suffix=None):
    """Load GUID by primary key, look up the corresponding view function in the
    routing table, and return the return value of the view function without
    changing the URL.

    :param str guid: GUID primary key
    :param str suffix: Remainder of URL after the GUID
    :return: Return value of proxied view function
    """
    # Look up GUID
    guid_object = Guid.load(guid)
    if guid_object:

        # verify that the object implements a GuidStoredObject-like interface. If a model
        #   was once GuidStoredObject-like but that relationship has changed, it's
        #   possible to have referents that are instances of classes that don't
        #   have a deep_url attribute or otherwise don't behave as
        #   expected.
        if not hasattr(guid_object.referent, 'deep_url'):
            sentry.log_message(
                'Guid `{}` resolved to an object with no deep_url'.format(guid)
            )
            raise HTTPError(http.NOT_FOUND)
        referent = guid_object.referent
        if referent is None:
            logger.error('Referent of GUID {0} not found'.format(guid))
            raise HTTPError(http.NOT_FOUND)
        if not referent.deep_url:
            raise HTTPError(http.NOT_FOUND)
        url = _build_guid_url(urllib.unquote(referent.deep_url), suffix)
        return proxy_url(url)

    # GUID not found; try lower-cased and redirect if exists
    guid_object_lower = Guid.load(guid.lower())
    if guid_object_lower:
        return redirect(
            _build_guid_url(guid.lower(), suffix)
        )

    # GUID not found
    raise HTTPError(http.NOT_FOUND)


# Redirects #

# redirect osf.io/about/ to OSF wiki page osf.io/4znzp/wiki/home/
def redirect_about(**kwargs):
    return redirect('https://osf.io/4znzp/wiki/home/')

def redirect_help(**kwargs):
    return redirect('/faq/')


# redirect osf.io/howosfworks to osf.io/getting-started/
def redirect_howosfworks(**kwargs):
    return redirect('/getting-started/')


# redirect osf.io/getting-started to help.osf.io/
def redirect_getting_started(**kwargs):
    return redirect('http://help.osf.io/')


# Redirect to home page
def redirect_to_home():
    return redirect('/')


def redirect_to_cos_news(**kwargs):
    # Redirect to COS News page
    return redirect('https://cos.io/news/')
