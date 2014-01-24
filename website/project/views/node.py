# -*- coding: utf-8 -*-
import json
import logging
import httplib as http
from framework import (
    request, redirect, must_be_logged_in,
    push_errors_to_status, get_current_user, Q,
    analytics
)
from framework.analytics import update_counters
import framework.status as status
from framework.exceptions import HTTPError
from framework.forms.utils import sanitize
from framework.mongo.utils import from_mongo
from framework.auth import must_have_session_auth, get_api_key

from website.models import Node
from website.project import new_node, clean_template_name
from website.project.decorators import must_not_be_registration, must_be_valid_project, \
    must_be_contributor, must_be_contributor_or_public
from website.project.forms import NewProjectForm, NewNodeForm
from website.models import WatchConfig
from website import settings
from website.views import _render_nodes

from .log import _get_logs

logger = logging.getLogger(__name__)


@must_have_session_auth
@must_be_valid_project  # returns project
@must_be_contributor  # returns user, project
@must_not_be_registration
def edit_node(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    node_to_use = node or project
    post_data = request.json
    edited_field = post_data.get('name')
    value = sanitize(post_data.get("value"))
    user = get_current_user()
    api_key = get_api_key()
    if value:
        if edited_field == 'title':
            node_to_use.set_title(value, user=user,
                                  api_key=api_key)
        elif edited_field == 'description':
            node_to_use.set_description(value, user=user, api_key=api_key)
        node_to_use.save()
    return {'status': 'success'}


##############################################################################
# New Project
##############################################################################


@must_be_logged_in
def project_new(*args, **kwargs):
    return {}


@must_be_logged_in
def project_new_post(*args, **kwargs):
    user = kwargs['user']
    form = NewProjectForm(request.form)
    if form.validate():
        project = new_node(
            'project', form.title.data, user, form.description.data
        )
        status.push_status_message(
            'Welcome to your new {category}! Please select and configure your add-ons below.'.format(
                category=project.project_or_component,
            )
        )
        return {}, 201, None, project.url + 'settings/'
    else:
        push_errors_to_status(form.errors)
    return {}, http.BAD_REQUEST


##############################################################################
# New Node
##############################################################################


@must_have_session_auth # returns user
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def project_new_node(*args, **kwargs):
    form = NewNodeForm(request.form)
    project = kwargs['project']
    user = kwargs['user']
    if form.validate():
        node = new_node(
            title=form.title.data,
            user=user,
            category=form.category.data,
            project=project,
        )
        status.push_status_message(
            'Welcome to your new {category}! Please select and configure your add-ons below.'.format(
                category=node.project_or_component,
            )
        )
        return {
            'status': 'success',
        }, 201, None, node.url + 'settings/'
    else:
        push_errors_to_status(form.errors)
    raise HTTPError(http.BAD_REQUEST, redirect_url=project.url)


@must_have_session_auth
@must_be_valid_project  # returns project
@must_not_be_registration
def project_before_fork(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    user = kwargs['user']
    api_key = get_api_key()

    prompts = node.callback('before_fork', user)

    return {'prompts': prompts}


@must_be_logged_in
@must_be_valid_project
def node_fork_page(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = get_current_user()
    api_key = get_api_key()

    if node:
        node_to_use = node
        status.push_status_message('At this time, only projects can be forked; however, this behavior is coming soon.')
        raise HTTPError(
            http.FORBIDDEN,
            message='At this time, only projects can be forked; however, this behavior is coming soon.',
            redirect_url=node_to_use.url
        )
    else:
        node_to_use = project

    if node_to_use.is_registration:
        raise HTTPError(http.FORBIDDEN)

    fork = node_to_use.fork_node(user, api_key=api_key)

    return fork.url


@must_be_valid_project
@must_be_contributor_or_public# returns user, project
@update_counters('node:{pid}')
@update_counters('node:{nid}')
def node_registrations(*args, **kwargs):
    user = get_current_user()
    node_to_use = kwargs['node'] or kwargs['project']
    link = kwargs['link']
    return _view_project(node_to_use, user, link, primary=True)


@must_be_valid_project
@must_be_contributor_or_public # returns user, project
@update_counters('node:{pid}')
@update_counters('node:{nid}')
def node_forks(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = get_current_user()
    link = kwargs['link']
    node_to_use = node or project
    return _view_project(node_to_use, user, link, primary=True)


@must_be_valid_project
@must_be_contributor # returns user, project
def node_setting(**kwargs):

    user = get_current_user()
    node = kwargs.get('node') or kwargs.get('project')

    if not node.is_public and not node.can_edit(user):
        raise HTTPError(http.FORBIDDEN)

    rv = _view_project(node, user, primary=True)

    addons_enabled = []
    addon_enabled_settings = []

    for addon in node.get_addons():

        addons_enabled.append(addon.config.short_name)

        if 'node' in addon.config.configs:
            addon_enabled_settings.append(addon.config.short_name)

    rv['addon_categories'] = settings.ADDON_CATEGORIES
    rv['addons_available'] = [
        addon
        for addon in settings.ADDONS_AVAILABLE
        if 'node' in addon.owners
    ]
    rv['addons_enabled'] = addons_enabled
    rv['addon_enabled_settings'] = addon_enabled_settings
    rv['addon_capabilities'] = settings.ADDON_CAPABILITIES

    return rv


@must_be_contributor
@must_not_be_registration
def node_choose_addons(**kwargs):
    node = kwargs['node'] or kwargs['project']
    node.config_addons(request.json)


##############################################################################
# View Project
##############################################################################


@must_be_valid_project
@must_not_be_registration
@must_be_contributor # returns user, project
def project_reorder_components(*args, **kwargs):
    project = kwargs['project']
    user = get_current_user()

    node_to_use = project
    old_list = [i._id for i in node_to_use.nodes if not i.is_deleted]
    new_list = json.loads(request.form['new_list'])

    if len(old_list) == len(new_list) and set(new_list) == set(old_list):
        node_to_use.nodes = new_list
        if node_to_use.save():
            return {'status': 'success'}
    # todo log impossibility
    return {'status': 'failure'}


##############################################################################


@must_be_valid_project
@must_be_contributor_or_public # returns user, project
def project_statistics(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = get_current_user()

    # todo not used
    node_to_use = node or project

    counters = analytics.get_day_total_list(
        'node:{}'.format(node_to_use._primary_key)
    )
    csv = '\\n'.join(['date,price'] + ['{},{}'.format(counter[0], counter[1]) for counter in counters])

    rv = {
        'csv' : csv,
    }
    if not node_to_use.is_public and not node_to_use.can_edit(user):
        raise HTTPError(http.FORBIDDEN)
    else:
        rv.update(_view_project(node_to_use, user, primary=True))
        return rv


###############################################################################
# Make Public
###############################################################################


@must_have_session_auth
@must_be_valid_project
@must_be_contributor
def project_set_permissions(*args, **kwargs):

    user = kwargs['user']
    api_key = kwargs['api_key']
    permissions = kwargs['permissions']
    node_to_use = kwargs['node'] or kwargs['project']

    node_to_use.set_permissions(permissions, user, api_key)

    return {
        'status': 'success',
        'permissions': permissions,
        'redirect_url': node_to_use.url
    }, None, None


@must_have_session_auth  # returns user or api_node
@must_be_valid_project  # returns project
@must_be_contributor_or_public
@must_not_be_registration
def watch_post(*args, **kwargs):
    node_to_use = kwargs['node'] or kwargs['project']
    user = kwargs['user']
    watch_config = WatchConfig(node=node_to_use,
                               digest=request.json.get('digest', False),
                               immediate=request.json.get('immediate', False))
    try:
        user.watch(watch_config)
    except ValueError:  # Node is already being watched
        raise HTTPError(http.BAD_REQUEST)
    watch_config.save()
    user.save()
    return {
        'status': 'success',
        'watchCount': len(node_to_use.watchconfig__watched)
    }


@must_have_session_auth  # returns user or api_node
@must_be_valid_project  # returns project
@must_be_contributor_or_public
@must_not_be_registration
def unwatch_post(*args, **kwargs):
    node_to_use = kwargs['node'] or kwargs['project']
    user = kwargs['user']
    watch_config = WatchConfig(node=node_to_use,
                                digest=request.json.get('digest', False),
                                immediate=request.json.get('immediate', False))
    try:
        user.unwatch(watch_config, save=True)
    except ValueError:  # Node isn't being watched
        raise HTTPError(http.BAD_REQUEST)
    return {
        'status': 'success',
        'watchCount': len(node_to_use.watchconfig__watched)
    }


@must_have_session_auth  # returns user or api_node
@must_be_valid_project  # returns project
@must_be_contributor_or_public
@must_not_be_registration
def togglewatch_post(*args, **kwargs):
    '''View for toggling watch mode for a node.'''
    node = kwargs['node'] or kwargs['project']
    user = kwargs['user']
    watch_config = WatchConfig(node=node,
                                digest=request.json.get('digest', False),
                                immediate=request.json.get('immediate', False))
    try:
        if user.is_watching(node):
            user.unwatch(watch_config, save=True)
        else:
            user.watch(watch_config, save=True)
    except ValueError:
        raise HTTPError(http.BAD_REQUEST)
    return {
        'status': 'success',
        'watchCount': len(node.watchconfig__watched),
        'watched': user.is_watching(node)
    }


@must_have_session_auth # returns user or api_node
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def component_remove(*args, **kwargs):
    """Remove component, and recursively remove its children. If node has a
    parent, add log and redirect to parent; else redirect to user dashboard.

    """
    node_to_use = kwargs['node'] or kwargs['project']
    user = kwargs['user']

    if node_to_use.remove_node(user=user):
        message = '{} deleted'.format(
            node_to_use.project_or_component.capitalize()
        )
        status.push_status_message(message)
        if node_to_use.node__parent:
            redirect_url = node_to_use.node__parent[0].url
        else:
            redirect_url = '/dashboard/'
        return {
            'status': 'success',
            'message': message,
        }, None, None, redirect_url
    else:
        raise HTTPError(http.BAD_REQUEST, message='Could not delete component')


@must_be_valid_project
@must_be_contributor_or_public
def view_project(*args, **kwargs):
    user = get_current_user()
    node_to_use = kwargs['node'] or kwargs['project']
    link = kwargs['link']
    primary = '/api/v1' not in request.path
    rv = _view_project(node_to_use, user, link, primary=primary)
    rv['addon_capabilities'] = settings.ADDON_CAPABILITIES
    return rv

@must_have_session_auth # returns user or api_node
@must_be_valid_project # returns project
@must_be_contributor
def remove_private_link(*args, **kwargs):
    node_to_use = kwargs['node'] or kwargs['project']
    link = request.json['private_link']
    node_to_use.remove_private_link(link)




# TODO: Split into separate functions
def _render_addon(node):

    widgets = {}
    configs = {}
    js = []
    css = []

    for addon in node.get_addons():

        configs[addon.config.short_name] = addon.config.to_json()

        js.extend(addon.config.include_js.get('widget', []))
        css.extend(addon.config.include_css.get('widget', []))

        if node.has_files:
            js.extend(addon.config.include_js.get('files', []))
            css.extend(addon.config.include_css.get('files', []))

    if node.has_files:
        js.extend([
            '/static/vendor/jquery-drag-drop/jquery.event.drag-2.2.js',
            '/static/vendor/jquery-drag-drop/jquery.event.drop-2.2.js',
            '/static/vendor/dropzone/dropzone.js',
            '/static/js/slickgrid.custom.min.js',
            '/static/js/hgrid.js',
        ])
        css.extend([
            '/static/css/hgrid-base.css',
        ])

    return widgets, configs, js, css


def _view_project(node, user, link='', api_key=None, primary=False):
    """Build a JSON object containing everything needed to render

    project.view.mako.

    """
    parent = node.parent
    recent_logs = _get_logs(node, 10, user, api_key)
    widgets, configs, js, css = _render_addon(node)
    # Before page load callback; skip if not primary call
    if primary:
        for addon in node.get_addons():
            messages = addon.before_page_load(node, user) or []
            for message in messages:
                status.push_status_message(message)
    data = {
        'node': {
            'id': node._primary_key,
            'title': node.title,
            'category': node.project_or_component,
            'description': node.description,
            'url': node.url,
            'api_url': node.api_url,
            'absolute_url': node.absolute_url,
            'display_absolute_url': node.display_absolute_url,
            'citations': {
                'apa': node.citation_apa,
                'mla': node.citation_mla,
                'chicago': node.citation_chicago,
            },
            'is_public': node.is_public,
            'date_created': node.date_created.strftime('%m/%d/%Y %I:%M %p UTC'),
            'date_modified': node.logs[-1].date.strftime('%m/%d/%Y %I:%M %p UTC') if node.logs else '',

            'tags': [tag._primary_key for tag in node.tags],
            'children': bool(node.nodes),
            'children_ids': [str(child._primary_key) for child in node.nodes],
            'is_registration': node.is_registration,
            'registered_from_url': node.registered_from.url if node.is_registration else '',
            'registered_date': node.registered_date.strftime('%Y/%m/%d %I:%M %p') if node.is_registration else '',
            'registered_meta': [
                {
                    'name_no_ext': from_mongo(meta),
                    'name_clean': clean_template_name(meta),
                }
                for meta in node.registered_meta or []
            ],
            'registration_count': len(node.registration_list),

            'is_fork': node.is_fork,
            'forked_from_id': node.forked_from._primary_key if node.is_fork else '',
            'forked_from_display_absolute_url': node.forked_from.display_absolute_url if node.is_fork else '',
            'forked_date': node.forked_date.strftime('%Y/%m/%d %I:%M %p') if node.is_fork else '',
            'fork_count': len(node.fork_list),

            'watched_count': len(node.watchconfig__watched),
            'private_links': node.private_links,
            'link': link,
            'logs': recent_logs,
            'piwik_site_id': node.piwik_site_id,
        },
        'parent': {
            'id': parent._primary_key if parent else '',
            'title': parent.title if parent else '',
            'url': parent.url if parent else '',
            'api_url': parent.api_url if parent else '',
            'absolute_url':  parent.absolute_url if parent else '',
            'is_public': parent.is_public if parent else '',
            'is_contributor': parent.is_contributor(user) if parent else '',
            'can_be_viewed': (link in parent.private_links) if parent else False
        },
        'user': {
            'is_contributor': node.is_contributor(user),
            'can_edit': (node.can_edit(user, api_key)
                                and not node.is_registration),
            'can_view': node.can_view(user, link, api_key),
            'is_watching': user.is_watching(node) if user and not user == None else False,
            'piwik_token': user.piwik_token if user else '',
        },
        # TODO: Namespace with nested dicts
        'has_files': node.has_files,
        'addons_enabled': node.get_addon_names(),
        'addons': configs,
        'addon_widgets': widgets,
        'addon_widget_js': js,
        'addon_widget_css': css,
    }
    return data


def _get_children(node, user, indent=0):

    children = []

    for child in node.nodes:
        if node.can_view(user):
            children.append({
                'id': child._primary_key,
                'title': child.title,
                'indent': indent,
            })
            children.extend(_get_children(child, user, indent+1))

    return children


@must_be_valid_project
def get_editable_children(*args, **kwargs):

    node_to_use = kwargs['node'] or kwargs['project']
    user = get_current_user()

    if not node_to_use.can_edit(user):
        return

    children = _get_children(node_to_use, user)

    return {'children': children}


def _get_user_activity(node, user, rescale_ratio):

    # Counters
    total_count = len(node.logs)

    # Note: It's typically much faster to find logs of a given node
    # attached to a given user using node.logs.find(...) than by
    # loading the logs into Python and checking each one. However,
    # using deep caching might be even faster down the road.

    if user:
        ua_count = node.logs.find(Q('user', 'eq', user)).count()
    else:
        ua_count = 0

    non_ua_count = total_count - ua_count # base length of blue bar

    # Normalize over all nodes
    try:
        ua = ua_count / rescale_ratio * settings.USER_ACTIVITY_MAX_WIDTH
    except ZeroDivisionError:
        ua = 0
    try:
        non_ua = non_ua_count / rescale_ratio * settings.USER_ACTIVITY_MAX_WIDTH
    except ZeroDivisionError:
        non_ua = 0

    return ua_count, ua, non_ua

@must_be_valid_project
def get_recent_logs(*args, **kwargs):
    node_to_use = kwargs['node'] or kwargs['project']
    logs = list(reversed(node_to_use.logs._to_primary_keys()))[:3]
    return {'logs': logs}

@must_be_valid_project
def get_summary(*args, **kwargs):

    user = get_current_user()
    api_key = get_api_key()
    rescale_ratio = kwargs.get('rescale_ratio')
    node_to_use = kwargs['node'] or kwargs['project']
    link = request.args.get('key', '').strip('/')

    if node_to_use.can_view(user, link, api_key):
        summary = {
            'can_view': True,
            'id': node_to_use._primary_key,
            'url': node_to_use.url,
            'api_url': node_to_use.api_url,
            'title': node_to_use.title,
            'is_registration': node_to_use.is_registration,
            'registered_date': node_to_use.registered_date.strftime('%m/%d/%y %I:%M %p') if node_to_use.is_registration else None,
            'nlogs': None,
            'ua_count': None,
            'ua': None,
            'non_ua': None,
            'addons_enabled': node_to_use.get_addon_names(),
        }
        if rescale_ratio:
            ua_count, ua, non_ua = _get_user_activity(node_to_use, user, rescale_ratio)
            summary.update({
                'nlogs': len(node_to_use.logs),
                'ua_count': ua_count,
                'ua': ua,
                'non_ua': non_ua,
            })
    else:
        summary = {
            'can_view': False,
        }
    # TODO: Make output format consistent with _view_project
    return {
        'summary': summary,
    }

@must_be_contributor_or_public
def get_children(*args, **kwargs):
    node_to_use = kwargs['node'] or kwargs['project']
    return _render_nodes([
        node
        for node in node_to_use.nodes
        if not node.is_deleted
    ])

@must_be_contributor_or_public
def get_forks(*args, **kwargs):
    node_to_use = kwargs['node'] or kwargs['project']
    forks = node_to_use.node__forked.find(
        Q('is_deleted', 'eq', False)
    )
    return _render_nodes(forks)

@must_be_contributor_or_public
def get_registrations(*args, **kwargs):
    node_to_use = kwargs['node'] or kwargs['project']
    registrations = node_to_use.node__registrations
    return _render_nodes(registrations)

@must_be_valid_project # returns project
@must_be_contributor # returns user, project
def project_generate_private_link_post(*args, **kwargs):
    """ Add contributors to a node. """

    node_to_use = kwargs['node'] or kwargs['project']
    node_ids = request.json.get('node_ids', [])
    link = node_to_use.add_private_link()

    for node_id in node_ids:
        node = Node.load(node_id)
        node.add_private_link(link)

    return {'status': 'success'}, 201
