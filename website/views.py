# -*- coding: utf-8 -*-
import logging
import itertools
import math
import httplib as http

from modularodm import Q
from flask import request

from framework import utils
from framework import sentry
from framework.auth.core import User
from framework.flask import redirect  # VOL-aware redirect
from framework.routing import proxy_url
from framework.exceptions import HTTPError
from framework.auth.forms import SignInForm
from framework.forms import utils as form_utils
from framework.guid.model import GuidStoredObject
from framework.auth.forms import RegistrationForm
from framework.auth.forms import ResetPasswordForm
from framework.auth.forms import ForgotPasswordForm
from framework.auth.decorators import collect_auth
from framework.auth.decorators import must_be_logged_in

from website.models import Guid
from website.models import Node
from website.util import rubeus
from website.util import sanitize
from website.project import model
from website.util import web_url_for
from website.util import permissions
from website.project import new_dashboard
from website.settings import ALL_MY_PROJECTS_ID
from website.settings import ALL_MY_REGISTRATIONS_ID

logger = logging.getLogger(__name__)


def _rescale_ratio(auth, nodes):
    """Get scaling denominator for log lists across a sequence of nodes.

    :param nodes: Nodes
    :return: Max number of logs

    """
    if not nodes:
        return 0
    counts = [
        len(node.logs)
        for node in nodes
        if node.can_view(auth)
    ]
    if counts:
        return float(max(counts))
    return 0.0


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
        'rescale_ratio': _rescale_ratio(auth, nodes),
        'show_path': show_path
    }
    return ret


@collect_auth
def index(auth):
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

    return_value['timezone'] = user.timezone
    return_value['locale'] = user.locale
    return_value['id'] = user._id
    return return_value


@must_be_logged_in
def get_all_projects_smart_folder(auth, **kwargs):
    # TODO: Unit tests
    user = auth.user

    contributed = user.node__contributed
    nodes = contributed.find(
        Q('is_deleted', 'eq', False) &
        Q('is_registration', 'eq', False) &
        Q('is_folder', 'eq', False)
    ).sort('-title')

    keys = nodes.get_keys()
    return [rubeus.to_project_root(node, auth, **kwargs) for node in nodes if node.parent_id not in keys]

@must_be_logged_in
def get_all_registrations_smart_folder(auth, **kwargs):
    # TODO: Unit tests
    user = auth.user
    contributed = user.node__contributed

    nodes = contributed.find(

        Q('is_deleted', 'eq', False) &
        Q('is_registration', 'eq', True) &
        Q('is_folder', 'eq', False)
    ).sort('-title')

    # Note(hrybacki): is_retracted and pending_embargo are property methods
    # and cannot be directly queried
    nodes = filter(lambda node: not node.is_retracted and not node.pending_embargo, nodes)
    keys = [node._id for node in nodes]
    return [rubeus.to_project_root(node, auth, **kwargs) for node in nodes if node.ids_above.isdisjoint(keys)]

@must_be_logged_in
def get_dashboard_nodes(auth):
    """Get summary information about the current user's dashboard nodes.

    :param-query no_components: Exclude components from response.
        NOTE: By default, components will only be shown if the current user
        is contributor on a comonent but not its parent project. This query
        parameter forces ALL components to be excluded from the request.
    :param-query permissions: Filter upon projects for which the current user
        has the specified permissions. Examples: 'write', 'admin'
    """
    user = auth.user

    contributed = user.node__contributed  # nodes user contributed to

    nodes = contributed.find(
        Q('category', 'eq', 'project') &
        Q('is_deleted', 'eq', False) &
        Q('is_registration', 'eq', False) &
        Q('is_folder', 'eq', False)
    )

    if request.args.get('no_components') not in [True, 'true', 'True', '1', 1]:
        comps = contributed.find(
            # components only
            Q('category', 'ne', 'project') &
            # exclude deleted nodes
            Q('is_deleted', 'eq', False) &
            # exclude registrations
            Q('is_registration', 'eq', False)
        )
    else:
        comps = []

    nodes = list(nodes) + list(comps)
    if request.args.get('permissions'):
        perm = request.args['permissions'].strip().lower()
        if perm not in permissions.PERMISSIONS:
            raise HTTPError(http.BAD_REQUEST, dict(
                message_short='Invalid query parameter',
                message_long='{0} is not in {1}'.format(perm, permissions.PERMISSIONS)
            ))
        response_nodes = [node for node in nodes if node.has_permission(user, permission=perm)]
    else:
        response_nodes = nodes
    return _render_nodes(response_nodes, auth)


@must_be_logged_in
def dashboard(auth):
    user = auth.user
    dashboard_folder = find_dashboard(user)
    dashboard_id = dashboard_folder._id
    return {'addons_enabled': user.get_addon_names(),
            'dashboard_id': dashboard_id,
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
        "logs": [serialize_log(log) for log in logs],
        "total": total,
        "pages": pages,
        "page": page
    }


def serialize_log(node_log, auth=None, anonymous=False):
    '''Return a dictionary representation of the log.'''
    return {
        'id': str(node_log._primary_key),
        'user': node_log.user.serialize()
        if isinstance(node_log.user, User)
        else {'fullname': node_log.foreign_user},
        'contributors': [node_log._render_log_contributor(c) for c in node_log.params.get("contributors", [])],
        'action': node_log.action,
        'params': sanitize.unescape_entities(node_log.params),
        'date': utils.iso8601format(node_log.date),
        'node': node_log.node.serialize(auth) if node_log.node else None,
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


# GUID ###

def _build_guid_url(base, suffix=None):
    url = '/'.join([
        each.strip('/') for each in [base, suffix]
        if each
    ])
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
        if not referent.deep_url:
            raise HTTPError(http.NOT_FOUND)
        url = _build_guid_url(referent.deep_url, suffix)
        return proxy_url(url)

    # GUID not found; try lower-cased and redirect if exists
    guid_object_lower = Guid.load(guid.lower())
    if guid_object_lower:
        return redirect(
            _build_guid_url(guid.lower(), suffix)
        )

    # GUID not found
    raise HTTPError(http.NOT_FOUND)

##### Redirects #####

# Redirect /about/ to OSF wiki page
# https://github.com/CenterForOpenScience/osf.io/issues/3862
# https://github.com/CenterForOpenScience/community/issues/294
def redirect_about(**kwargs):
    return redirect('https://osf.io/4znzp/wiki/home/')


def redirect_howosfworks(**kwargs):
    return redirect('/getting-started/')
