# -*- coding: utf-8 -*-
import itertools
import httplib as http
import logging
import math
import os
import urllib

from django.apps import apps
from modularodm import Q
from modularodm.exceptions import NoResultsFound
from flask import request, send_from_directory

from framework import utils, sentry
from framework.auth.decorators import must_be_logged_in
from framework.auth.forms import SignInForm, ForgotPasswordForm
from framework.exceptions import HTTPError
from framework.flask import redirect  # VOL-aware redirect
from framework.forms import utils as form_utils
from framework.routing import proxy_url
from website.institutions.views import view_institution

from website.models import Guid
from website.models import Institution, PreprintService
from website.project import new_bookmark_collection
from website.settings import EXTERNAL_EMBER_APPS
from website.util import permissions

logger = logging.getLogger(__name__)


def _render_node(node, auth=None, parent_node=None):
    """

    :param node:
    :return:

    """
    NodeRelation = apps.get_model('osf.NodeRelation')
    perm = None
    # NOTE: auth.user may be None if viewing public project while not
    # logged in
    if auth and auth.user and node.get_permissions(auth.user):
        perm_list = node.get_permissions(auth.user)
        perm = permissions.reduce_permissions(perm_list)

    if parent_node:
        try:
            node_relation = parent_node.node_relations.get(child__id=node.id)
        except NodeRelation.DoesNotExist:
            primary = False
            _id = node._id
        else:
            primary = not node_relation.is_node_link
            _id = node._id if primary else node_relation._id
    else:
        _id = node._id
        primary = True
    return {
        'title': node.title,
        'id': _id,
        'url': node.url,
        'api_url': node.api_url,
        'primary': primary,
        'date_modified': utils.iso8601format(node.date_modified),
        'category': node.category,
        'permissions': perm,  # A string, e.g. 'admin', or None,
        'archiving': node.archiving,
        'is_retracted': node.is_retracted,
        'is_registration': node.is_registration,
    }


def _render_nodes(nodes, auth=None, show_path=False, parent_node=None):
    """

    :param nodes:
    :return:
    """
    ret = {
        'nodes': [
            _render_node(node, auth=auth, parent_node=parent_node)
            for node in nodes
        ],
        'show_path': show_path
    }
    return ret


def index():
    try:
        #TODO : make this way more robust
        institution = Institution.find_one(Q('domains', 'eq', request.host.lower()))
        inst_dict = view_institution(institution._id)
        inst_dict.update({
            'home': False,
            'institution': True,
            'redirect_url': '/institutions/{}/'.format(institution._id)
        })

        return inst_dict
    except NoResultsFound:
        pass

    all_institutions = Institution.find().sort('name')
    dashboard_institutions = [
        {'id': inst._id, 'name': inst.name, 'logo_path': inst.logo_path_rounded_corners}
        for inst in all_institutions
    ]

    return {
        'home': True,
        'dashboard_institutions': dashboard_institutions
    }


def find_bookmark_collection(user):
    Collection = apps.get_model('osf.Collection')
    bookmark_collection = Collection.find(Q('is_bookmark_collection', 'eq', True) & Q('creator', 'eq', user))
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


def reproducibility():
    return redirect('/ezcuj/wiki')


def signin_form():
    return form_utils.jsonify(SignInForm())


def forgot_password_form():
    return form_utils.jsonify(ForgotPasswordForm(prefix='forgot_password'))


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
    try:
        # Look up
        guid_object = Guid.load(guid)
    except KeyError as e:
        if e.message == 'osfstorageguidfile':  # Used when an old detached OsfStorageGuidFile object is accessed
            raise HTTPError(http.NOT_FOUND)
        else:
            raise e
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
        if isinstance(referent, PreprintService):
            return send_from_directory(
                os.path.abspath(os.path.join(os.getcwd(), EXTERNAL_EMBER_APPS['preprints']['path'])),
                'index.html'
            )
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
