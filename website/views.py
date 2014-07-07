# -*- coding: utf-8 -*-
import logging
import itertools
import httplib as http
from flask import request, redirect
from modularodm import Q

from framework.exceptions import HTTPError
from framework.forms import utils
from framework.routing import proxy_url
from framework.auth import Auth, get_current_user
from framework.auth.decorators import collect_auth, must_be_logged_in
from framework.auth.forms import (RegistrationForm, SignInForm,
                                  ForgotPasswordForm, ResetPasswordForm)

from website.models import Guid, Node
from website.util import web_url_for, rubeus
from website.project.forms import NewProjectForm, NewFolderForm
from website.project import model, new_dashboard, new_folder
from website import settings


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


def _render_projects(nodes, **kwargs):
    """

    :param nodes:
    :return:
    """
    pass
    ret = {'data': [rubeus.to_project_hgrid(node, **kwargs) for node in nodes]}
    return ret


def _render_dashboard(nodes, **kwargs):
    """

    :param nodes:
    :return:
    """
    dashboard_projects = [rubeus.to_project_hgrid(node, **kwargs) for node in nodes]
    ret = {'data': dashboard_projects}
    return ret



def _render_node(node):
    """

    :param node:
    :return:

    """
    return {
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
        Q('is_dashboard','eq', True)
    )

    if dashboard_folder.count() == 0:
        new_dashboard(user)
        dashboard_folder = user.node__contributed.find(
            Q('is_dashboard','eq', True)
        )
    return dashboard_folder


@must_be_logged_in
def get_dashboard(nid=None, **kwargs):
    user = kwargs['auth'].user
    if nid is None:
        nodes = find_dashboard(user)
        dashboard_projects = [rubeus.to_project_root(node, **kwargs) for node in nodes]
        return_value = {'data': dashboard_projects}
    elif nid == '-amp':
        return_value = get_all_projects_smart_folder(**kwargs)
    elif nid == '-amr':
        return_value = get_all_registrations_smart_folder(**kwargs)
    else:
        node = Node.load(nid)
        dashboard_projects = rubeus.to_project_hgrid(node, **kwargs)
        return_value = {'data': dashboard_projects}
    return return_value

@must_be_logged_in
def get_all_projects_smart_folder(**kwargs):

    user = kwargs['auth'].user

    nodes = user.node__contributed.find(
        Q('category', 'eq', 'project') &
        Q('is_deleted', 'eq', False) &
        Q('is_registration', 'eq', False) &
        Q('is_folder','eq', False)
    ).sort('-title')

    return_value = [rubeus.to_project_root(node, **kwargs) for node in nodes]
    return return_value

@must_be_logged_in
def get_all_registrations_smart_folder(**kwargs):

    user = kwargs['auth'].user

    nodes = user.node__contributed.find(
        Q('category', 'eq', 'project') &
        Q('is_deleted', 'eq', False) &
        Q('is_registration', 'eq', True) &
        Q('is_folder','eq', False)
    ).sort('-title')

    return_value = [rubeus.to_project_root(node, **kwargs) for node in nodes]
    return return_value

@must_be_logged_in
def get_dashboard_nodes(auth, **kwargs):
    user = auth.user

    contributed = user.node__contributed  # nodes user cotributed to

    nodes = contributed.find(
        Q('category', 'eq', 'project') &
        Q('is_deleted', 'eq', False) &
        Q('is_registration', 'eq', False) &
        Q('is_folder','eq', False)
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
def dashboard(**kwargs):
    auth = kwargs['auth']
    user = auth.user
    dashboard_folder = find_dashboard(user)
    dashboard_id = dashboard_folder[0]._id


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
            watch_logs.append(log.serialize())
        else:
            has_more_logs =True
            break

    return {"logs": watch_logs, "has_more_logs": has_more_logs}


def reproducibility():
    return redirect('/ezcuj/wiki')


def registration_form():
    return utils.jsonify(RegistrationForm(prefix='register'))


def signin_form():
    return utils.jsonify(SignInForm())


def forgot_password_form():
    return utils.jsonify(ForgotPasswordForm(prefix='forgot_password'))


def reset_password_form():
    return utils.jsonify(ResetPasswordForm())


def new_project_form():
    return utils.jsonify(NewProjectForm())

def new_folder_form():
    form = NewFolderForm()
    # form._fields['location']['choices'] = get_folders()
    # form.location.choices=get_folders()
    return utils.jsonify(form)



@must_be_logged_in
def get_folders(**kwargs):
    """Find the user's folder nodes

    :param User user: User object
    :return array of tuples with key, value of the nodes
    """
    auth = kwargs['auth']
    user = auth.user
    folders = user.node__contributed.find(
        Q('is_deleted', 'eq', False) &
        Q('is_registration', 'eq', False) &
        Q('is_folder','eq', True)
    )
    return [(folder._id, folder.title) for folder in folders]


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
        referent = guid_object.referent
        if referent is None:
            logger.error('Referent of GUID {0} not found'.format(guid))
            raise HTTPError(http.NOT_FOUND)
        mode = referent.redirect_mode
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
