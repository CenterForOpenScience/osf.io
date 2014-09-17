# -*- coding: utf-8 -*-
import logging
import itertools
import httplib as http

from flask import request, redirect
from modularodm import Q

from framework.auth.core import User
from framework import utils
from framework.forms import utils as form_utils
from framework import sentry
from framework.exceptions import HTTPError
from framework.routing import proxy_url
from framework.auth import Auth, get_current_user
from framework.auth.decorators import collect_auth, must_be_logged_in
from framework.auth.forms import (RegistrationForm, SignInForm,
                                  ForgotPasswordForm, ResetPasswordForm)
from framework.guid.model import GuidStoredObject
from website.models import Guid, Node
from website.util import web_url_for, rubeus
from website.project import model, new_dashboard
from website import settings

from website.settings import ALL_MY_REGISTRATIONS_ID, ALL_MY_PROJECTS_ID

logger = logging.getLogger(__name__)


def _rescale_ratio(nodes):
    """Get scaling denominator for log lists across a sequence of nodes.

    :param nodes: Nodes
    :return: Max number of logs

    """
    if not nodes:
        return 0
    user = get_current_user()
    counts = [
        len(node.logs)
        for node in nodes
        if node.can_view(Auth(user=user))
    ]
    if counts:
        return float(max(counts))
    return 0.0


def _render_node(node):
    """

    :param node:
    :return:

    """
    return {
        'title': node.title,
        'id': node._primary_key,
        'url': node.url,
        'api_url': node.api_url,
        'primary': node.primary,
    }


def _render_nodes(nodes):
    """

    :param nodes:
    :return:
    """
    ret = {
        'nodes': [
            _render_node(node)
            for node in nodes
        ],
        'rescale_ratio': _rescale_ratio(nodes),
    }
    return ret


def _get_user_activity(node, user, rescale_ratio):

    # Counters
    total_count = len(node.logs)

    # Note: It's typically much faster to find logs of a given node
    # attached to a given user using node.logs.find(...) than by
    # loading the logs into Python and checking each one. However,
    # using deep caching might be even faster down the road.

    ua_count = node.logs.find(Q('user', 'eq', user)).count()
    non_ua_count = total_count - ua_count # base length of blue bar

    # Normalize over all nodes
    ua = ua_count / rescale_ratio * settings.USER_ACTIVITY_MAX_WIDTH
    non_ua = non_ua_count / rescale_ratio * settings.USER_ACTIVITY_MAX_WIDTH

    return ua_count, ua, non_ua


@collect_auth
def index(auth, **kwargs):
    """Redirect to dashboard if user is logged in, else show homepage.

    """
    if auth.user:
        return redirect(web_url_for('dashboard'))
    return {}


def find_dashboard(user):
    dashboard_folder = user.node__contributed.find(
        Q('is_dashboard', 'eq', True)
    )

    if dashboard_folder.count() == 0:
        new_dashboard(user)
        dashboard_folder = user.node__contributed.find(
            Q('is_dashboard', 'eq', True)
        )
    return dashboard_folder[0]


@must_be_logged_in
def get_dashboard(auth, nid=None, **kwargs):
    user = auth.user
    if nid is None:
        node = find_dashboard(user)
        dashboard_projects = [rubeus.to_project_root(node, auth, **kwargs)]
        return_value = {'data': dashboard_projects}
    elif nid == ALL_MY_PROJECTS_ID:
        return_value = {'data': get_all_projects_smart_folder(**kwargs)}
    elif nid == ALL_MY_REGISTRATIONS_ID:
        return_value = {'data': get_all_registrations_smart_folder(**kwargs)}
    else:
        node = Node.load(nid)
        dashboard_projects = rubeus.to_project_hgrid(node, auth, **kwargs)
        return_value = {'data': dashboard_projects}
    return return_value

@must_be_logged_in
def get_all_projects_smart_folder(auth, **kwargs):

    user = auth.user

    contributed = user.node__contributed

    nodes = contributed.find(
        Q('category', 'eq', 'project') &
        Q('is_deleted', 'eq', False) &
        Q('is_registration', 'eq', False) &
        Q('is_folder', 'eq', False) &
        # parent is not in the nodes list
        Q('__backrefs.parent.node.nodes', 'eq', None)
    ).sort('-title')

    comps = contributed.find(
        # components only
        Q('category', 'ne', 'project') &
        # parent is not in the nodes list
        Q('__backrefs.parent.node.nodes', 'nin', nodes.get_keys()) &
        # exclude deleted nodes
        Q('is_deleted', 'eq', False) &
        # exclude registrations
        Q('is_registration', 'eq', False)
    )

    return_value = [rubeus.to_project_root(comp, auth, **kwargs) for comp in comps]
    return_value.extend([rubeus.to_project_root(node, auth, **kwargs) for node in nodes])
    return return_value

@must_be_logged_in
def get_all_registrations_smart_folder(auth, **kwargs):

    user = auth.user
    contributed = user.node__contributed

    nodes = contributed.find(
        Q('category', 'eq', 'project') &
        Q('is_deleted', 'eq', False) &
        Q('is_registration', 'eq', True) &
        Q('is_folder', 'eq', False) &
        # parent is not in the nodes list
        Q('__backrefs.parent.node.nodes', 'eq', None)
    ).sort('-title')

    comps = contributed.find(
        # components only
        Q('category', 'ne', 'project') &
        # parent is not in the nodes list
        Q('__backrefs.parent.node.nodes', 'nin', nodes.get_keys()) &
        # exclude deleted nodes
        Q('is_deleted', 'eq', False) &
        # exclude registrations
        Q('is_registration', 'eq', True)
    )

    return_value = [rubeus.to_project_root(comp, auth, **kwargs) for comp in comps]
    return_value.extend([rubeus.to_project_root(node, auth, **kwargs) for node in nodes])
    return return_value

@must_be_logged_in
def get_dashboard_nodes(auth, **kwargs):
    user = auth.user

    contributed = user.node__contributed  # nodes user contributed to

    nodes = contributed.find(
        Q('category', 'eq', 'project') &
        Q('is_deleted', 'eq', False) &
        Q('is_registration', 'eq', False) &
        Q('is_folder', 'eq', False)
    )

    comps = contributed.find(
        # components only
        Q('category', 'ne', 'project') &
        # parent is not in the nodes list
        Q('__backrefs.parent.node.nodes', 'nin', nodes.get_keys()) &
        # exclude deleted nodes
        Q('is_deleted', 'eq', False) &
        # exclude registrations
        Q('is_registration', 'eq', False)
    )

    return _render_nodes(list(nodes) + list(comps))


@must_be_logged_in
def dashboard(auth):
    user = auth.user
    dashboard_folder = find_dashboard(user)
    dashboard_id = dashboard_folder._id

    return {'addons_enabled': user.get_addon_names(),
            'dashboard_id': dashboard_id
            }


@must_be_logged_in
def watched_logs_get(**kwargs):
    user = kwargs['auth'].user
    page_num = int(request.args.get('pageNum', '').strip('/') or 0)
    page_size = 10
    offset = page_num * page_size
    recent_log_ids = itertools.islice(user.get_recent_log_ids(), offset, offset + page_size + 1)
    logs = (model.NodeLog.load(id) for id in recent_log_ids)
    watch_logs = []
    has_more_logs = False

    for log in logs:
        if len(watch_logs) < page_size:
            watch_logs.append(serialize_log(log))
        else:
            has_more_logs =True
            break

    return {"logs": watch_logs, "has_more_logs": has_more_logs}


def serialize_log(node_log, anonymous=False):
    '''Return a dictionary representation of the log.'''
    return {
        'id': str(node_log._primary_key),
        'user': node_log.user.serialize()
                if isinstance(node_log.user, User)
                else {'fullname': node_log.foreign_user},
        'contributors': [node_log._render_log_contributor(c) for c in node_log.params.get("contributors", [])],
        'api_key': node_log.api_key.label if node_log.api_key else '',
        'action': node_log.action,
        'params': node_log.params,
        'date': utils.rfcformat(node_log.date),
        'node': node_log.node.serialize() if node_log.node else None,
        'anonymous': anonymous
    }


def reproducibility():
    return redirect('/ezcuj/wiki')


def registration_form():
    return form_utils.jsonify(RegistrationForm(prefix='register'))


def signin_form():
    return form_utils.jsonify(SignInForm())


def forgot_password_form():
    return form_utils.jsonify(ForgotPasswordForm(prefix='forgot_password'))


def reset_password_form():
    return form_utils.jsonify(ResetPasswordForm())


### GUID ###

def _build_guid_url(url, prefix=None, suffix=None):
    if not url.startswith('/'):
        url = '/' + url
    if not url.endswith('/'):
        url += '/'
    url = (
        (prefix or '') +
        url +
        (suffix or '')
    )
    if not url.endswith('/'):
        url += '/'
    return url


def resolve_guid(guid, suffix=None):
    """Resolve GUID to corresponding URL and return result of appropriate
    view function. This effectively yields a redirect without changing the
    displayed URL of the page.

    :param guid: GUID value (not the object)
    :param suffix: String to append to GUID route
    :return: Werkzeug response

    """
    # Get prefix; handles API routes
    prefix = request.path.split(guid)[0].rstrip('/')

    # Look up GUID
    guid_object = Guid.load(guid)
    if guid_object:

        # verify that the object is a GuidStoredObject descendant. If a model
        #   was once a descendant but that relationship has changed, it's
        #   possible to have referents that are instances of classes that don't
        #   have a redirect_mode attribute or otherwise don't behave as
        #   expected.
        if not isinstance(guid_object.referent, GuidStoredObject):
            sentry.log_message(
                'Guid `{}` resolved to non-guid object'.format(guid)
            )

            raise HTTPError(http.NOT_FOUND)

        referent = guid_object.referent
        if referent is None:
            logger.error('Referent of GUID {0} not found'.format(guid))
            raise HTTPError(http.NOT_FOUND)
        mode = referent.redirect_mode
        if mode is None:
            raise HTTPError(http.NOT_FOUND)
        url = referent.deep_url if mode == 'proxy' else referent.url
        url = _build_guid_url(url, prefix, suffix)
        # Always redirect API URLs; URL should identify endpoint being called
        if prefix or mode == 'redirect':
            if request.query_string:
                url += '?' + request.query_string
            return redirect(url)
        return proxy_url(url)

    # GUID not found; try lower-cased and redirect if exists
    guid_object_lower = Guid.load(guid.lower())
    if guid_object_lower:
        return redirect(
            _build_guid_url(
                guid.lower(), prefix, suffix
            )
        )

    # GUID not found
    raise HTTPError(http.NOT_FOUND)
