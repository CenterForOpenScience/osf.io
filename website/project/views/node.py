# -*- coding: utf-8 -*-
import json
import logging
import httplib as http
from bs4 import BeautifulSoup
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

from website.project import new_node, clean_template_name
from website.project.decorators import must_not_be_registration, must_be_valid_project, \
    must_be_contributor, must_be_contributor_or_public
from website.project.forms import NewProjectForm, NewNodeForm
from website.models import WatchConfig
from website import settings
from website.views import _render_nodes

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
@must_be_contributor_or_public # returns user, project
@update_counters('node:{pid}')
@update_counters('node:{nid}')
def node_registrations(*args, **kwargs):

    user = get_current_user()
    node_to_use = kwargs['node'] or kwargs['project']
    return _view_project(node_to_use, user)

@must_be_valid_project
@must_be_contributor_or_public # returns user, project
@update_counters('node:{pid}')
@update_counters('node:{nid}')
def node_forks(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = get_current_user()

    node_to_use = node or project
    return _view_project(node_to_use, user)


@must_be_valid_project
@must_be_contributor # returns user, project
def node_setting(**kwargs):

    user = get_current_user()
    node = kwargs.get('node') or kwargs.get('project')

    rv = _view_project(node, user)

    addon_data = {}
    addon_enabled_settings = []

    for addon_name in node.addons_enabled:

        registered_addon = settings.ADDONS_AVAILABLE_DICT[addon_name]

        if registered_addon.schema is None or registered_addon.settings_model is None:
            continue

        Schema = registered_addon.settings_model
        backref_key = '__'.join([Schema._name, 'addons'])

        addons = getattr(node, backref_key)

        if addons:

            addon_data[addon_name] = {
                'schema': json.dumps(registered_addon.schema),
                'settings': addons[0].meta_json(),
            }

            addon_enabled_settings.append(addon_name)

    rv['addon_settings'] = addon_data
    rv['addon_categories'] = settings.ADDON_CATEGORIES

    rv['addons_available'] = settings.ADDONS_AVAILABLE
    rv['addons_enabled'] = node.addons_enabled
    rv['addon_enabled_settings'] = addon_enabled_settings

    return rv


@must_be_contributor_or_public
def node_choose_addons(**kwargs):

    node = kwargs.get('node') or kwargs.get('project')

    for addon, enabled in request.json.iteritems():

        registered_addon = settings.ADDONS_AVAILABLE_DICT[addon]

        if enabled:

            Schema = registered_addon.settings_model
            if Schema is None:
                continue

            if addon not in node.addons_enabled:
                node.addons_enabled.append(addon)
                node._order_addons()
                node.save()

            backref_key = '__'.join([Schema._name, 'addons'])
            models = getattr(node, backref_key)
            if not models:
                model = Schema(node=node)
                model.save()

        else:

            try:
                node.addons_enabled.remove(addon)
                node.save()
            except ValueError:
                pass


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
    rv.update(_view_project(node_to_use, user))
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
    return _view_project(node_to_use, user)


def _render_addon(node):

    widgets = {}
    tabs = {}
    icons = {}
    js = []
    css = []

    for addon in node.addons_enabled:

        registered_addon = settings.ADDONS_AVAILABLE_DICT[addon]
        Schema = registered_addon.settings_model

        if Schema is None:
            continue

        backref_key = '__'.join([Schema._name, 'addons'])
        addons = getattr(node, backref_key)

        if addons:

            #try:
            #    widgets[addon] = addons[0].render_widget()
            #except NotImplementedError:
            #    pass
            widget = registered_addon.widget_json(addons[0])
            if widget:
                widgets[addon] = widget

            try:
                tabs[addon] = addons[0].render_tab()
            except AttributeError:
                pass

            if registered_addon.icon:
                icons[addon] = registered_addon.icon_url

            js.extend(registered_addon.include_js.get('widget', []))
            css.extend(registered_addon.include_css.get('widget', []))

    return widgets, tabs, icons, js, css


def _view_project(node_to_use, user, api_key=None):
    """Build a JSON object containing everything needed to render
    project.view.mako.

    """
    parent = node_to_use.parent
    recent_logs = list(reversed(node_to_use.logs)[:10])
    recent_logs_dicts = [log.serialize() for log in recent_logs]
    widgets, tabs, icons, js, css = _render_addon(node_to_use)
    data = {
        'node': {
            'id': node_to_use._primary_key,
            'title': node_to_use.title,
            'category': node_to_use.project_or_component,
            'description': node_to_use.description,
            'url': node_to_use.url,
            'api_url': node_to_use.api_url,
            'absolute_url': node_to_use.absolute_url,
            'display_absolute_url': node_to_use.display_absolute_url,
            'citations': {
                'apa': node_to_use.citation_apa,
                'mla': node_to_use.citation_mla,
                'chicago': node_to_use.citation_chicago,
            },
            'is_public': node_to_use.is_public,
            'date_created': node_to_use.date_created.strftime('%m/%d/%Y %I:%M %p UTC'),
            'date_modified': node_to_use.logs[-1].date.strftime('%m/%d/%Y %I:%M %p UTC') if node_to_use.logs else '',

            'tags': [tag._primary_key for tag in node_to_use.tags],
            'children': bool(node_to_use.nodes),
            'children_ids': [str(child._primary_key) for child in node_to_use.nodes],
            'is_registration': node_to_use.is_registration,
            'registered_from_url': node_to_use.registered_from.url if node_to_use.is_registration else '',
            'registered_date': node_to_use.registered_date.strftime('%Y/%m/%d %I:%M %p') if node_to_use.is_registration else '',
            'registered_meta': [
                {
                    'name_no_ext': from_mongo(meta),
                    'name_clean': clean_template_name(meta),
                }
                for meta in node_to_use.registered_meta or []
            ],
            'registration_count': len(node_to_use.registration_list),

            'is_fork': node_to_use.is_fork,
            'forked_from_id': node_to_use.forked_from._primary_key if node_to_use.is_fork else '',
            'forked_from_display_absolute_url': node_to_use.forked_from.display_absolute_url if node_to_use.is_fork else '',
            'forked_date': node_to_use.forked_date.strftime('%Y/%m/%d %I:%M %p') if node_to_use.is_fork else '',
            'fork_count': len(node_to_use.fork_list),

            'watched_count': len(node_to_use.watchconfig__watched),
            'logs': recent_logs_dicts
        },
        'parent': {
            'id': parent._primary_key if parent else '',
            'title': parent.title if parent else '',
            'url': parent.url if parent else '',
            'api_url': parent.api_url if parent else '',
            'absolute_url':  parent.absolute_url if parent else '',
            'is_public': parent.is_public if parent else '',
            'is_contributor': parent.is_contributor(user) if parent else ''
        },
        'user': {
            'is_contributor': node_to_use.is_contributor(user),
            'can_edit': (node_to_use.can_edit(user, api_key)
                                and not node_to_use.is_registration),
            'is_watching': user.is_watching(node_to_use) if user else False
        },
        'addons_enabled': node_to_use.addons_enabled,
        'addon_widgets': widgets,
        'addon_tabs': tabs,
        'addon_icons': icons,
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
        return redirect('/login/?next={0}'.format(request.path))

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

    widgets, tabs, icons, _, _ = _render_addon(node_to_use)

    if node_to_use.can_view(user, api_key):
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
            'icons': icons,
            'addons_enabled': node_to_use.addons_enabled,
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
