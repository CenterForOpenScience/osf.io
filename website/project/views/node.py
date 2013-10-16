# -*- coding: utf-8 -*-
import re
import json
import httplib as http

from framework import (
    request, redirect, must_be_logged_in, push_status_message,
    push_errors_to_status, get_current_user, update_counters, Q
)
from framework import HTTPError
from .. import new_node, new_project
from ..decorators import must_not_be_registration, must_be_valid_project, \
    must_be_contributor, must_be_contributor_or_public
from ..forms import NewProjectForm, NewNodeForm
from ..model import User, WatchConfig
from framework.forms.utils import sanitize
from framework.auth import must_have_session_auth, get_api_key

from .. import clean_template_name

from website import settings
from website import filters
from website.views import _render_nodes

from framework import analytics


@must_have_session_auth #
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def edit_node(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']

    node_to_use = node or project

    form = request.form
    original_title = node_to_use.title

    if form.get('name') == 'title' and form.get('value'):
        node_to_use.title = sanitize(form['value'])

        node_to_use.add_log(
            action='edit_title',
            params={
                'project':node_to_use.node__parent[0]._primary_key if node_to_use.node__parent else None,
                'node':node_to_use._primary_key,
                'title_new':node_to_use.title,
                'title_original':original_title,
            },
            user=get_current_user(),
            api_key=get_api_key(),
        )

        node_to_use.save()

    return {'status' : 'success'}

def search_user(*args, **kwargs):
    form = request.form
    query = form.get('query', '').strip()

    is_email = False
    email_re = re.search('[^@\s]+@[^@\s]+\.[^@\s]+', query)
    if email_re:
        is_email = True
        email = email_re.group(0)
        result = User.find_by_email(email)
    else:
        result = User.search(query)

    return {
        'is_email':is_email,
        'results':[
            {
                'fullname' : item.fullname,
                'gravatar' : filters.gravatar(
                    item.username,
                    use_ssl=True,
                    size=settings.gravatar_size_add_contributor
                ),
                'id' : item._primary_key,
            } for item in result
        ]
    }

##############################################################################
# New Project
##############################################################################

@must_be_logged_in
def project_new_post(*args, **kwargs):
    user = kwargs['user']
    form = NewProjectForm(request.form)
    if form.validate():
        project = new_project(form.title.data, form.description.data, user)
        return redirect('/project/' + str(project._primary_key))
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
            project = project,
        )
        return {
            'status' : 'success',
        }, 201, None, project.url
        # return redirect('/project/' + str(project._primary_key))
    else:
        push_errors_to_status(form.errors)
    # todo: raise error
    raise HTTPError(http.BAD_REQUEST, redirect_url=project.url)
    # return redirect('/project/' + str(project._primary_key))

@must_be_valid_project
def node_fork_page(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = get_current_user()
    api_key = get_api_key()

    if node:
        node_to_use = node
        push_status_message('At this time, only projects can be forked; however, this behavior is coming soon.')
        # todo discuss
        # return redirect(node_to_use.url)
        raise HTTPError(
            http.FORBIDDEN,
            message='At this time, only projects can be forked; however, this behavior is coming soon.',
            redirect_url=node_to_use.url
        )
    else:
        node_to_use = project

    if node_to_use.is_registration:
        raise HTTPError(http.FORBIDDEN)
        # push_status_message('At this time, only projects that are not registrations can be forked; however, this behavior is coming soon.')
        # # todo discuss
        # return node_to_use.url

    fork = node_to_use.fork_node(user, api_key=api_key)

    return fork.url

@must_have_session_auth
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
def node_setting(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = get_current_user()

    node_to_use = node or project

    return _view_project(node_to_use, user)

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
            return {'status' : 'success'}
    # todo log impossibility
    return {'success' : 'failure'}

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

    return {'status' : 'success'}, None, None, node_to_use.url


@must_have_session_auth  # returns user or api_node
@must_be_valid_project  # returns project
@must_be_contributor_or_public
@must_not_be_registration
def watch_post(*args, **kwargs):
    node_to_use = kwargs['node'] or kwargs['project']
    user = kwargs['user']

    _config = WatchConfig(node=node_to_use,
                                digest=request.form.get("digest", False),
                                immediate=request.form.get('immediate', False))
    try:
        user.watch(watch_config)
    except ValueError:  # Node is already being watched
        raise HTTPError(http.BAD_REQUEST)
    watch_config.save()
    user.save()
    return {'status': 'success', 'watchCount': len(node_to_use.watchconfig__watched)}

@must_have_session_auth  # returns user or api_node
@must_be_valid_project  # returns project
@must_be_contributor_or_public
@must_not_be_registration
def unwatch_post(*args, **kwargs):
    node_to_use = kwargs['node'] or kwargs['project']
    user = kwargs['user']
    watch_config = WatchConfig(node=node_to_use,
                                digest=request.form.get("digest", False),
                                immediate=request.form.get('immediate', False))
    try:
        user.unwatch(watch_config, save=True)
    except ValueError:  # Node isn't being watched
        raise HTTPError(http.BAD_REQUEST)
    return {'status': 'success', 'watchCount': len(node_to_use.watchconfig__watched)}


@must_have_session_auth  # returns user or api_node
@must_be_valid_project  # returns project
@must_be_contributor_or_public
@must_not_be_registration
def togglewatch_post(*args, **kwargs):
    '''View for toggling watch mode for a node.'''
    node = kwargs['node'] or kwargs['project']
    user = kwargs['user']
    watch_config = WatchConfig(node=node,
                                digest=request.form.get("digest", False),
                                immediate=request.form.get('immediate', False))
    try:
        if user.is_watching(node):
            user.unwatch(watch_config, save=True)
        else:
            user.watch(watch_config, save=True)
    except ValueError:
        raise HTTPError(http.BAD_REQUEST)
    return {'status': 'success',
            'watchCount': len(node.watchconfig__watched),
            "watched": user.is_watching(node)
            }


@must_have_session_auth # returns user or api_node
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def component_remove(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    if node:
        node_to_use = node
    else:
        node_to_use = project

    if node_to_use.remove_node(user=user):
        category = 'project' \
            if node_to_use.category == 'project' \
            else 'component'
        message = '{} deleted'.format(category.capitalize())
        push_status_message(message)
        return {
            'status' : 'success',
            'message' : message,
        }, None, None, '/dashboard/'
    else:
        raise HTTPError(http.BAD_REQUEST, message='Could not delete component')


@must_be_valid_project
@must_be_contributor_or_public
def view_project(*args, **kwargs):
    user = get_current_user()
    node_to_use = kwargs['node'] or kwargs['project']
    return _view_project(node_to_use, user)

def _view_project(node_to_use, user):
    '''Build a JSON object containing everything needed to render
    project.view.mako.

    '''
    return {
        'node_id' : node_to_use._primary_key,
        'node_title' : node_to_use.title,
        'node_category' : 'project'
            if node_to_use.category == 'project'
            else 'component',
        'node_description' : node_to_use.description,
        'node_url' : node_to_use.url,
        'node_api_url' : node_to_use.api_url,
        'node_is_public' : node_to_use.is_public,
        'node_date_created' : node_to_use.date_created.strftime('%Y/%m/%d %I:%M %p'),
        'node_date_modified' : node_to_use.logs[-1].date.strftime('%Y/%m/%d %I:%M %p'),

        'node_tags' : [tag._primary_key for tag in node_to_use.tags],
        'node_children' : bool(node_to_use.nodes),

        'node_is_registration' : node_to_use.is_registration,
        'node_registered_from_url' : node_to_use.registered_from.url if node_to_use.is_registration else '',
        'node_registered_date' : node_to_use.registered_date.strftime('%Y/%m/%d %I:%M %p') if node_to_use.is_registration else '',
        'node_registered_meta' : [
            {
                'name_no_ext' : meta.replace('.txt', ''),
                'name_clean' : clean_template_name(meta),
            }
            for meta in node_to_use.registered_meta or []
        ],
        'node_registration_count' : len(node_to_use.registration_list),

        'node_is_fork' : node_to_use.is_fork,
        'node_forked_from_url' : node_to_use.forked_from.url if node_to_use.is_fork else '',
        'node_forked_date' : node_to_use.forked_date.strftime('%Y/%m/%d %I:%M %p') if node_to_use.is_fork else '',
        'node_fork_count' : len(node_to_use.fork_list),

        'node_watched_count': len(node_to_use.watchconfig__watched),
        'parent_id' : node_to_use.node__parent[0]._primary_key if node_to_use.node__parent else None,
        'parent_title' : node_to_use.node__parent[0].title if node_to_use.node__parent else None,
        'parent_url' : node_to_use.node__parent[0].url if node_to_use.node__parent else None,

        'user_is_contributor' : node_to_use.is_contributor(user),
        'user_can_edit' : node_to_use.is_contributor(user) and not node_to_use.is_registration,
        'user_is_watching': user.is_watching(node_to_use) if user else False,
    }


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
        ua = ua_count / rescale_ratio * settings.user_activity_max_width
    except ZeroDivisionError:
        ua = 0
    try:
        non_ua = non_ua_count / rescale_ratio * settings.user_activity_max_width
    except ZeroDivisionError:
        non_ua = 0

    return ua_count, ua, non_ua

@must_be_valid_project
def get_recent_logs(*args, **kwargs):
    node_to_use = kwargs['node'] or kwargs['project']
    logs = list(reversed(node_to_use.logs._to_primary_keys()))[:3]
    return {'logs' : logs}

@must_be_valid_project
def get_summary(*args, **kwargs):

    user = get_current_user()
    api_key = get_api_key()
    rescale_ratio = kwargs.get('rescale_ratio')
    node_to_use = kwargs['node'] or kwargs['project']

    can_edit = node_to_use.can_edit(user, api_key)

    summary = {
        'id': node_to_use._primary_key,
        'url': node_to_use.url,
        'api_url': node_to_use.api_url,
        'title': node_to_use.title if can_edit else node_to_use.public_title,
        'is_registration': node_to_use.is_registration,
        'registered_date': node_to_use.registered_date.strftime('%m/%d/%y %I:%M %p') if node_to_use.is_registration else None,
        'show_logs': can_edit or node_to_use.are_logs_public,
        'show_contributors': can_edit or node_to_use.are_contributors_public,
        'nlogs': None,
        'ua_count': None,
        'ua': None,
        'non_ua': None,
    }

    if rescale_ratio and (can_edit or node_to_use.are_logs_public):
        ua_count, ua, non_ua = _get_user_activity(node_to_use, user, rescale_ratio)
        summary.update({
            'nlogs': len(node_to_use.logs),
            'ua_count': ua_count,
            'ua': ua,
            'non_ua': non_ua,
        })
    return {
        'summary': summary,
    }

@must_be_contributor_or_public
def get_children(*args, **kwargs):
    node_to_use = kwargs['node'] or kwargs['project']
    return _render_nodes(node_to_use.nodes)

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
