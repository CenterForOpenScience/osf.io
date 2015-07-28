# -*- coding: utf-8 -*-
import logging
import httplib as http
import math
from itertools import islice

from flask import request
from modularodm import Q
from modularodm.exceptions import ModularOdmException, ValidationValueError

from framework import status
from framework.utils import iso8601format
from framework.mongo import StoredObject
from framework.auth.decorators import must_be_logged_in, collect_auth
from framework.exceptions import HTTPError, PermissionsError
from framework.mongo.utils import from_mongo, get_or_http_error

from website import language

from website.util import paths
from website.util import rubeus
from website.exceptions import NodeStateError
from website.project import clean_template_name, new_node, new_private_link
from website.project.decorators import (
    must_be_contributor_or_public,
    must_be_contributor,
    must_be_valid_project,
    must_have_permission,
    must_not_be_registration,
)
from website.util.permissions import ADMIN, READ, WRITE
from website.util.rubeus import collect_addon_js
from website.project.model import has_anonymous_link, get_pointer_parent, NodeUpdateError
from website.project.forms import NewNodeForm
from website.models import Node, Pointer, WatchConfig, PrivateLink
from website import settings
from website.views import _render_nodes, find_dashboard, validate_page_num
from website.profile import utils
from website.project import new_folder
from website.util.sanitize import strip_html

logger = logging.getLogger(__name__)

@must_be_valid_project
@must_have_permission(WRITE)
@must_not_be_registration
def edit_node(auth, node, **kwargs):
    post_data = request.json
    edited_field = post_data.get('name')
    value = strip_html(post_data.get('value', ''))
    if edited_field == 'title':
        try:
            node.set_title(value, auth=auth)
        except ValidationValueError as e:
            raise HTTPError(
                http.BAD_REQUEST,
                data=dict(message_long=e.message)
            )
    elif edited_field == 'description':
        node.set_description(value, auth=auth)
    node.save()
    return {'status': 'success'}


##############################################################################
# New Project
##############################################################################


@must_be_logged_in
def project_new(**kwargs):
    return {}

@must_be_logged_in
def project_new_post(auth, **kwargs):
    user = auth.user

    data = request.get_json()
    title = strip_html(data.get('title'))
    title = title.strip()
    category = data.get('category', 'project')
    template = data.get('template')
    description = strip_html(data.get('description'))
    new_project = {}

    if template:
        original_node = Node.load(template)
        changes = {
            'title': title,
            'category': category,
            'template_node': original_node,
        }

        if description:
            changes['description'] = description

        project = original_node.use_as_template(
            auth=auth,
            changes={
                template: changes,
            }
        )

    else:
        try:
            project = new_node(category, title, user, description)
        except ValidationValueError as e:
            raise HTTPError(
                http.BAD_REQUEST,
                data=dict(message_long=e.message)
            )
        new_project = _view_project(project, auth)
    return {
        'projectUrl': project.url,
        'newNode': new_project['node'] if new_project else None
    }, http.CREATED


@must_be_logged_in
@must_be_valid_project
def project_new_from_template(auth, node, **kwargs):
    new_node = node.use_as_template(
        auth=auth,
        changes=dict(),
    )
    return {'url': new_node.url}, http.CREATED, None

##############################################################################
# New Folder
##############################################################################
@must_be_valid_project
@must_be_logged_in
def folder_new_post(auth, node, **kwargs):
    user = auth.user

    title = request.json.get('title')

    if not node.is_folder:
        raise HTTPError(http.BAD_REQUEST)
    folder = new_folder(strip_html(title), user)
    folders = [folder]
    try:
        _add_pointers(node, folders, auth)
    except ValueError:
        raise HTTPError(http.BAD_REQUEST)

    return {
        'projectUrl': '/dashboard/',
    }, http.CREATED


@collect_auth
def add_folder(auth, **kwargs):
    data = request.get_json()
    node_id = data.get('node_id')
    node = get_or_http_error(Node, node_id)

    user = auth.user
    title = strip_html(data.get('title'))
    if not node.is_folder:
        raise HTTPError(http.BAD_REQUEST)

    folder = new_folder(
        title, user
    )
    folders = [folder]
    try:
        _add_pointers(node, folders, auth)
    except ValueError:
        raise HTTPError(http.BAD_REQUEST)
    return {}, 201, None

##############################################################################
# New Node
##############################################################################

@must_be_valid_project
@must_have_permission(WRITE)
@must_not_be_registration
def project_new_node(auth, node, **kwargs):
    form = NewNodeForm(request.form)
    user = auth.user
    if form.validate():
        try:
            new_component = new_node(
                title=strip_html(form.title.data),
                user=user,
                category=form.category.data,
                parent=node,
            )
        except ValidationValueError as e:
            raise HTTPError(
                http.BAD_REQUEST,
                data=dict(message_long=e.message)
            )

        message = (
            'Your component was created successfully. You can keep working on the component page below, '
            'or return to the <u><a href="{url}">project page</a></u>.'
        ).format(url=node.url)
        status.push_status_message(message, kind='info', trust=True)

        return {
            'status': 'success',
        }, 201, None, new_component.url
    else:
        # TODO: This function doesn't seem to exist anymore?
        status.push_errors_to_status(form.errors)
    raise HTTPError(http.BAD_REQUEST, redirect_url=node.url)


@must_be_logged_in
@must_be_valid_project
def project_before_fork(auth, node, **kwargs):
    user = auth.user

    prompts = node.callback('before_fork', user=user)

    if node.has_pointers_recursive:
        prompts.append(
            language.BEFORE_FORK_HAS_POINTERS.format(
                category=node.project_or_component
            )
        )

    return {'prompts': prompts}


@must_be_logged_in
@must_be_valid_project
def project_before_template(auth, node, **kwargs):
    prompts = []

    for addon in node.get_addons():
        if 'node' in addon.config.configs:
            if addon.to_json(auth.user)['addon_full_name']:
                prompts.append(addon.to_json(auth.user)['addon_full_name'])

    return {'prompts': prompts}


@must_be_logged_in
@must_be_valid_project
def node_fork_page(auth, node, **kwargs):
    if settings.DISK_SAVING_MODE:
        raise HTTPError(
            http.METHOD_NOT_ALLOWED,
            redirect_url=node.url
        )
    try:
        fork = node.fork_node(auth)
    except PermissionsError:
        raise HTTPError(
            http.FORBIDDEN,
            redirect_url=node.url
        )
    return fork.url


@must_be_valid_project
@must_be_contributor_or_public
def node_registrations(auth, node, **kwargs):
    return _view_project(node, auth, primary=True)


@must_be_valid_project
@must_be_contributor_or_public
def node_forks(auth, node, **kwargs):
    return _view_project(node, auth, primary=True)


@must_be_valid_project
@must_be_logged_in
@must_be_contributor
def node_setting(auth, node, **kwargs):

    ret = _view_project(node, auth, primary=True)

    addons_enabled = []
    addon_enabled_settings = []

    for addon in node.get_addons():
        addons_enabled.append(addon.config.short_name)
        if 'node' in addon.config.configs:
            config = addon.to_json(auth.user)
            # inject the MakoTemplateLookup into the template context
            # TODO inject only short_name and render fully client side
            config['template_lookup'] = addon.config.template_lookup
            config['addon_icon_url'] = addon.config.icon_url
            addon_enabled_settings.append(config)
    addon_enabled_settings = sorted(addon_enabled_settings, key=lambda addon: addon['addon_full_name'].lower())

    ret['addon_categories'] = settings.ADDON_CATEGORIES
    ret['addons_available'] = sorted([
        addon
        for addon in settings.ADDONS_AVAILABLE
        if 'node' in addon.owners
        and addon.short_name not in settings.SYSTEM_ADDED_ADDONS['node']
    ], key=lambda addon: addon.full_name.lower())

    ret['addons_enabled'] = addons_enabled
    ret['addon_enabled_settings'] = addon_enabled_settings
    ret['addon_capabilities'] = settings.ADDON_CAPABILITIES

    ret['addon_js'] = collect_node_config_js(node.get_addons())

    ret['comments'] = {
        'level': node.comment_level,
    }

    ret['categories'] = Node.CATEGORY_MAP
    ret['categories'].update({
        'project': 'Project'
    })

    return ret
def collect_node_config_js(addons):
    """Collect webpack bundles for each of the addons' node-cfg.js modules. Return
    the URLs for each of the JS modules to be included on the node addons config page.

    :param list addons: List of node's addon config records.
    """
    js_modules = []
    for addon in addons:
        js_path = paths.resolve_addon_path(addon.config, 'node-cfg.js')
        if js_path:
            js_modules.append(js_path)
    return js_modules


@must_have_permission(WRITE)
@must_not_be_registration
def node_choose_addons(auth, node, **kwargs):
    node.config_addons(request.json, auth)


@must_be_valid_project
@must_have_permission(READ)
def node_contributors(auth, node, **kwargs):
    ret = _view_project(node, auth, primary=True)
    ret['contributors'] = utils.serialize_contributors(node.contributors, node)
    ret['adminContributors'] = utils.serialize_contributors(node.admin_contributors, node, admin=True)
    return ret


@must_have_permission(ADMIN)
def configure_comments(node, **kwargs):
    comment_level = request.json.get('commentLevel')
    if not comment_level:
        node.comment_level = None
    elif comment_level in ['public', 'private']:
        node.comment_level = comment_level
    else:
        raise HTTPError(http.BAD_REQUEST)
    node.save()


##############################################################################
# View Project
##############################################################################

@must_be_valid_project(retractions_valid=True)
@must_be_contributor_or_public
def view_project(auth, node, **kwargs):
    primary = '/api/v1' not in request.path
    ret = _view_project(node, auth, primary=primary)
    ret['addon_capabilities'] = settings.ADDON_CAPABILITIES
    # Collect the URIs to the static assets for addons that have widgets
    ret['addon_widget_js'] = list(collect_addon_js(
        node,
        filename='widget-cfg.js',
        config_entry='widget'
    ))
    ret.update(rubeus.collect_addon_assets(node))
    return ret


# Expand/Collapse
@must_be_valid_project
@must_be_contributor_or_public
def expand(auth, node, **kwargs):
    node.expand(user=auth.user)
    return {}, 200, None


@must_be_valid_project
@must_be_contributor_or_public
def collapse(auth, node, **kwargs):
    node.collapse(user=auth.user)
    return {}, 200, None


# Reorder components
@must_be_valid_project
@must_not_be_registration
@must_have_permission(WRITE)
def project_reorder_components(node, **kwargs):
    """Reorders the components in a project's component list.

    :param-json list new_list: List of strings that include node IDs and
        node type delimited by ':'.

    """
    # TODO(sloria): Change new_list parameter to be an array of objects
    # {
    #   'newList': {
    #       {'key': 'abc123', 'type': 'node'}
    #   }
    # }
    new_list = [
        tuple(n.split(':'))
        for n in request.json.get('new_list', [])
    ]
    nodes_new = [
        StoredObject.get_collection(schema).load(key)
        for key, schema in new_list
    ]

    valid_nodes = [
        n for n in node.nodes
        if not n.is_deleted
    ]
    deleted_nodes = [
        n for n in node.nodes
        if n.is_deleted
    ]
    if len(valid_nodes) == len(nodes_new) and set(valid_nodes) == set(nodes_new):
        node.nodes = nodes_new + deleted_nodes
        node.save()
        return {}

    logger.error('Got invalid node list in reorder components')
    raise HTTPError(http.BAD_REQUEST)


##############################################################################


@must_be_valid_project
@must_be_contributor_or_public
def project_statistics(auth, node, **kwargs):
    if not (node.can_edit(auth) or node.is_public):
        raise HTTPError(http.FORBIDDEN)
    return _view_project(node, auth, primary=True)


###############################################################################
# Make Private/Public
###############################################################################


@must_be_valid_project
@must_have_permission(ADMIN)
def project_before_set_public(node, **kwargs):
    prompt = node.callback('before_make_public')
    anonymous_link_warning = any(private_link.anonymous for private_link in node.private_links_active)
    if anonymous_link_warning:
        prompt.append('Anonymized view-only links <b>DO NOT</b> anonymize '
                      'contributors after a project or component is made public.')

    return {
        'prompts': prompt
    }


@must_be_valid_project
@must_have_permission(ADMIN)
def project_set_privacy(auth, node, **kwargs):

    permissions = kwargs.get('permissions')
    if permissions is None:
        raise HTTPError(http.BAD_REQUEST)

    try:
        node.set_privacy(permissions, auth)
    except NodeStateError as e:
        raise HTTPError(http.BAD_REQUEST, data=dict(
            message_short="Can't change privacy",
            message_long=e.message
        ))

    return {
        'status': 'success',
        'permissions': permissions,
    }


@must_be_valid_project
@must_be_contributor_or_public
@must_not_be_registration
def watch_post(auth, node, **kwargs):
    user = auth.user
    watch_config = WatchConfig(node=node,
                               digest=request.json.get('digest', False),
                               immediate=request.json.get('immediate', False))
    try:
        user.watch(watch_config)
    except ValueError:  # Node is already being watched
        raise HTTPError(http.BAD_REQUEST)

    user.save()

    return {
        'status': 'success',
        'watchCount': len(node.watchconfig__watched)
    }


@must_be_valid_project
@must_be_contributor_or_public
@must_not_be_registration
def unwatch_post(auth, node, **kwargs):
    user = auth.user
    watch_config = WatchConfig(node=node,
                               digest=request.json.get('digest', False),
                               immediate=request.json.get('immediate', False))
    try:
        user.unwatch(watch_config)
    except ValueError:  # Node isn't being watched
        raise HTTPError(http.BAD_REQUEST)

    return {
        'status': 'success',
        'watchCount': len(node.watchconfig__watched)
    }


@must_be_valid_project
@must_be_contributor_or_public
@must_not_be_registration
def togglewatch_post(auth, node, **kwargs):
    '''View for toggling watch mode for a node.'''
    # TODO: refactor this, watch_post, unwatch_post (@mambocab)
    user = auth.user
    watch_config = WatchConfig(
        node=node,
        digest=request.json.get('digest', False),
        immediate=request.json.get('immediate', False)
    )
    try:
        if user.is_watching(node):
            user.unwatch(watch_config)
        else:
            user.watch(watch_config)
    except ValueError:
        raise HTTPError(http.BAD_REQUEST)

    user.save()

    return {
        'status': 'success',
        'watchCount': len(node.watchconfig__watched),
        'watched': user.is_watching(node)
    }

@must_be_valid_project
@must_not_be_registration
@must_have_permission(WRITE)
def update_node(auth, node, **kwargs):
    # in node.update() method there is a key list node.WRITABLE_WHITELIST only allow user to modify
    # category, title, and discription which can be edited by write permission contributor
    try:
        return {
            'updated_fields': {
                key: getattr(node, key)
                for key in
                node.update(request.get_json(), auth=auth)
            }
        }
    except NodeUpdateError as e:
        raise HTTPError(400, data=dict(
            message_short="Failed to update attribute '{0}'".format(e.key),
            message_long=e.reason
        ))

@must_be_valid_project
@must_have_permission(ADMIN)
@must_not_be_registration
def component_remove(auth, node, **kwargs):
    """Remove component, and recursively remove its children. If node has a
    parent, add log and redirect to parent; else redirect to user dashboard.

    """
    try:
        node.remove_node(auth)
    except NodeStateError as e:
        raise HTTPError(
            http.BAD_REQUEST,
            data={
                'message_short': 'Error',
                'message_long': 'Could not delete component: ' + e.message
            },
        )
    node.save()

    message = '{} deleted'.format(
        node.project_or_component.capitalize()
    )
    status.push_status_message(message, kind='success', trust=False)
    parent = node.parent_node
    if parent and parent.can_view(auth):
        redirect_url = node.node__parent[0].url
    else:
        redirect_url = '/dashboard/'

    return {
        'url': redirect_url,
    }


@must_have_permission(ADMIN)
@must_not_be_registration
def delete_folder(auth, node, **kwargs):
    """Remove folder node

    """
    if node is None:
        raise HTTPError(http.BAD_REQUEST)

    if not node.is_folder or node.is_dashboard:
        raise HTTPError(http.BAD_REQUEST)

    try:
        node.remove_node(auth)
    except NodeStateError as e:
        raise HTTPError(
            http.BAD_REQUEST,
            data={
                'message_short': 'Error',
                'message_long': 'Could not delete component: ' + e.message
            },
        )

    return {}


@must_be_valid_project
@must_have_permission(ADMIN)
def remove_private_link(*args, **kwargs):
    link_id = request.json['private_link_id']

    try:
        link = PrivateLink.load(link_id)
        link.is_deleted = True
        link.save()
    except ModularOdmException:
        raise HTTPError(http.NOT_FOUND)


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

        js.extend(addon.config.include_js.get('files', []))
        css.extend(addon.config.include_css.get('files', []))

    return widgets, configs, js, css


def _should_show_wiki_widget(node, user):

    has_wiki = bool(node.get_addon('wiki'))
    wiki_page = node.get_wiki_page('home', None)
    if not node.has_permission(user, 'write'):
        return has_wiki and wiki_page and wiki_page.html(node)
    else:
        return has_wiki


def _view_project(node, auth, primary=False):
    """Build a JSON object containing everything needed to render
    project.view.mako.
    """
    user = auth.user

    parent = node.parent_node
    if user:
        dashboard = find_dashboard(user)
        dashboard_id = dashboard._id
        in_dashboard = dashboard.pointing_at(node._primary_key) is not None
    else:
        in_dashboard = False
        dashboard_id = ''
    view_only_link = auth.private_key or request.args.get('view_only', '').strip('/')
    anonymous = has_anonymous_link(node, auth)
    widgets, configs, js, css = _render_addon(node)
    redirect_url = node.url + '?view_only=None'

    # Before page load callback; skip if not primary call
    if primary:
        for addon in node.get_addons():
            messages = addon.before_page_load(node, user) or []
            for message in messages:
                status.push_status_message(message, kind='info', dismissible=False, trust=True)
    data = {
        'node': {
            'id': node._primary_key,
            'title': node.title,
            'category': node.category_display,
            'category_short': node.category,
            'node_type': node.project_or_component,
            'description': node.description or '',
            'url': node.url,
            'api_url': node.api_url,
            'absolute_url': node.absolute_url,
            'redirect_url': redirect_url,
            'display_absolute_url': node.display_absolute_url,
            'update_url': node.api_url_for('update_node'),
            'in_dashboard': in_dashboard,
            'is_public': node.is_public,
            'is_archiving': node.archiving,
            'date_created': iso8601format(node.date_created),
            'date_modified': iso8601format(node.logs[-1].date) if node.logs else '',
            'tags': [tag._primary_key for tag in node.tags],
            'children': bool(node.nodes),
            'is_registration': node.is_registration,
            'is_retracted': node.is_retracted,
            'pending_retraction': node.pending_retraction,
            'retracted_justification': getattr(node.retraction, 'justification', None),
            'embargo_end_date': node.embargo_end_date.strftime("%A, %b. %d, %Y") if node.embargo_end_date else False,
            'pending_embargo': node.pending_embargo,
            'registered_from_url': node.registered_from.url if node.is_registration else '',
            'registered_date': iso8601format(node.registered_date) if node.is_registration else '',
            'root_id': node.root._id,
            'registered_meta': [
                {
                    'name_no_ext': from_mongo(meta),
                    'name_clean': clean_template_name(meta),
                }
                for meta in node.registered_meta or []
            ],
            'registration_count': len(node.node__registrations),
            'is_fork': node.is_fork,
            'forked_from_id': node.forked_from._primary_key if node.is_fork else '',
            'forked_from_display_absolute_url': node.forked_from.display_absolute_url if node.is_fork else '',
            'forked_date': iso8601format(node.forked_date) if node.is_fork else '',
            'fork_count': len(node.forks),
            'templated_count': len(node.templated_list),
            'watched_count': len(node.watchconfig__watched),
            'private_links': [x.to_json() for x in node.private_links_active],
            'link': view_only_link,
            'anonymous': anonymous,
            'points': len(node.get_points(deleted=False, folders=False)),
            'piwik_site_id': node.piwik_site_id,
            'comment_level': node.comment_level,
            'has_comments': bool(getattr(node, 'commented', [])),
            'has_children': bool(getattr(node, 'commented', False)),
            'identifiers': {
                'doi': node.get_identifier_value('doi'),
                'ark': node.get_identifier_value('ark'),
            },
        },
        'parent_node': {
            'exists': parent is not None,
            'id': parent._primary_key if parent else '',
            'title': parent.title if parent else '',
            'category': parent.category_display if parent else '',
            'url': parent.url if parent else '',
            'api_url': parent.api_url if parent else '',
            'absolute_url': parent.absolute_url if parent else '',
            'registrations_url': parent.web_url_for('node_registrations') if parent else '',
            'is_public': parent.is_public if parent else '',
            'is_contributor': parent.is_contributor(user) if parent else '',
            'can_view': parent.can_view(auth) if parent else False
        },
        'user': {
            'is_contributor': node.is_contributor(user),
            'is_admin_parent': parent.is_admin_parent(user) if parent else False,
            'can_edit': (node.can_edit(auth)
                         and not node.is_registration),
            'has_read_permissions': node.has_permission(user, 'read'),
            'permissions': node.get_permissions(user) if user else [],
            'is_watching': user.is_watching(node) if user else False,
            'piwik_token': user.piwik_token if user else '',
            'id': user._id if user else None,
            'username': user.username if user else None,
            'fullname': user.fullname if user else '',
            'can_comment': node.can_comment(auth),
            'show_wiki_widget': _should_show_wiki_widget(node, user),
            'dashboard_id': dashboard_id,
        },
        'badges': _get_badge(user),
        # TODO: Namespace with nested dicts
        'addons_enabled': node.get_addon_names(),
        'addons': configs,
        'addon_widgets': widgets,
        'addon_widget_js': js,
        'addon_widget_css': css,
        'node_categories': Node.CATEGORY_MAP,
    }
    return data


def _get_badge(user):
    if user:
        badger = user.get_addon('badges')
        if badger:
            return {
                'can_award': badger.can_award,
                'badges': badger.get_badges_json()
            }
    return {}


def _get_children(node, auth, indent=0):

    children = []

    for child in node.nodes_primary:
        if not child.is_deleted and child.can_edit(auth):
            children.append({
                'id': child._primary_key,
                'title': child.title,
                'indent': indent,
                'is_public': child.is_public,
                'parent_id': child.parent_id,
            })
            children.extend(_get_children(child, auth, indent + 1))

    return children


@must_be_valid_project
@must_have_permission(ADMIN)
def private_link_table(node, **kwargs):
    data = {
        'node': {
            'absolute_url': node.absolute_url,
            'private_links': [x.to_json() for x in node.private_links_active],
        }
    }
    return data


@collect_auth
@must_be_valid_project
def get_editable_children(auth, node, **kwargs):

    if not node.can_edit(auth):
        return

    children = _get_children(node, auth)

    return {
        'node': {'id': node._id, 'title': node.title, 'is_public': node.is_public},
        'children': children,
    }


def _get_user_activity(node, auth, rescale_ratio):

    # Counters
    total_count = len(node.logs)

    # Note: It's typically much faster to find logs of a given node
    # attached to a given user using node.logs.find(...) than by
    # loading the logs into Python and checking each one. However,
    # using deep caching might be even faster down the road.

    if auth.user:
        ua_count = node.logs.find(Q('user', 'eq', auth.user)).count()
    else:
        ua_count = 0

    non_ua_count = total_count - ua_count  # base length of blue bar

    # Normalize over all nodes
    try:
        ua = ua_count / rescale_ratio * 100
    except ZeroDivisionError:
        ua = 0
    try:
        non_ua = non_ua_count / rescale_ratio * 100
    except ZeroDivisionError:
        non_ua = 0

    return ua_count, ua, non_ua


@must_be_valid_project
def get_recent_logs(node, **kwargs):
    logs = list(reversed(node.logs._to_primary_keys()))[:3]
    return {'logs': logs}


def _get_summary(node, auth, rescale_ratio, primary=True, link_id=None, show_path=False):
    # TODO(sloria): Refactor this or remove (lots of duplication with _view_project)
    summary = {
        'id': link_id if link_id else node._id,
        'primary': primary,
        'is_registration': node.is_registration,
        'is_fork': node.is_fork,
        'is_retracted': node.is_retracted,
        'pending_retraction': node.pending_retraction,
        'embargo_end_date': node.embargo_end_date.strftime("%A, %b. %d, %Y") if node.embargo_end_date else False,
        'pending_embargo': node.pending_embargo,
        'archiving': node.archiving,
    }

    if node.can_view(auth):
        summary.update({
            'can_view': True,
            'can_edit': node.can_edit(auth),
            'primary_id': node._id,
            'url': node.url,
            'primary': primary,
            'api_url': node.api_url,
            'title': node.title,
            'category': node.category,
            'node_type': node.project_or_component,
            'is_registration': node.is_registration,
            'anonymous': has_anonymous_link(node, auth),
            'registered_date': node.registered_date.strftime('%Y-%m-%d %H:%M UTC')
            if node.is_registration
            else None,
            'nlogs': None,
            'ua_count': None,
            'ua': None,
            'non_ua': None,
            'addons_enabled': node.get_addon_names(),
            'is_public': node.is_public,
            'parent_title': node.parent_node.title if node.parent_node else None,
            'parent_is_public': node.parent_node.is_public if node.parent_node else False,
            'show_path': show_path
        })
        if rescale_ratio:
            ua_count, ua, non_ua = _get_user_activity(node, auth, rescale_ratio)
            summary.update({
                'nlogs': len(node.logs),
                'ua_count': ua_count,
                'ua': ua,
                'non_ua': non_ua,
            })
    else:
        summary['can_view'] = False

    # TODO: Make output format consistent with _view_project
    return {
        'summary': summary,
    }


@collect_auth
@must_be_valid_project(retractions_valid=True)
def get_summary(auth, node, **kwargs):
    rescale_ratio = kwargs.get('rescale_ratio')
    if rescale_ratio is None and request.args.get('rescale_ratio'):
        try:
            rescale_ratio = float(request.args.get('rescale_ratio'))
        except (TypeError, ValueError):
            raise HTTPError(http.BAD_REQUEST)
    primary = kwargs.get('primary')
    link_id = kwargs.get('link_id')
    show_path = kwargs.get('show_path', False)

    return _get_summary(
        node, auth, rescale_ratio, primary=primary, link_id=link_id, show_path=show_path
    )


@must_be_contributor_or_public
def get_children(auth, node, **kwargs):
    user = auth.user
    if request.args.get('permissions'):
        perm = request.args['permissions'].lower().strip()
        nodes = [
            each
            for each in node.nodes
            if perm in each.get_permissions(user) and not each.is_deleted
        ]
    else:
        nodes = [
            each
            for each in node.nodes
            if not each.is_deleted
        ]
    return _render_nodes(nodes, auth)


@must_be_contributor_or_public
def get_folder_pointers(auth, node, **kwargs):
    if not node.is_folder:
        return []
    nodes = [
        each.resolve()._id
        for each in node.nodes
        if each is not None and not each.is_deleted and not each.primary
    ]
    return nodes


@must_be_contributor_or_public
def get_forks(auth, node, **kwargs):
    return _render_nodes(nodes=node.forks, auth=auth)


@must_be_contributor_or_public
def get_registrations(auth, node, **kwargs):
    registrations = [n for n in node.node__registrations if not n.is_deleted]  # get all registrations, including archiving
    return _render_nodes(registrations, auth)


@must_be_valid_project
@must_have_permission(ADMIN)
def project_generate_private_link_post(auth, node, **kwargs):
    """ creata a new private link object and add it to the node and its selected children"""

    node_ids = request.json.get('node_ids', [])
    name = request.json.get('name', '')
    anonymous = request.json.get('anonymous', False)

    if node._id not in node_ids:
        node_ids.insert(0, node._id)

    nodes = [Node.load(node_id) for node_id in node_ids]

    has_public_node = any(node.is_public for node in nodes)

    new_link = new_private_link(
        name=name, user=auth.user, nodes=nodes, anonymous=anonymous
    )

    if anonymous and has_public_node:
        status.push_status_message(
            'Anonymized view-only links <b>DO NOT</b> '
            'anonymize contributors of public project or component.',
            trust=True
        )

    return new_link


@must_be_valid_project
@must_have_permission(ADMIN)
def project_private_link_edit(auth, **kwargs):
    new_name = request.json.get('value', '')
    private_link_id = request.json.get('pk', '')
    private_link = PrivateLink.load(private_link_id)
    if private_link:
        private_link.name = new_name
        private_link.save()


def _serialize_node_search(node):
    """Serialize a node for use in pointer search.

    :param Node node: Node to serialize
    :return: Dictionary of node data

    """
    title = node.title
    if node.is_registration:
        title += ' (registration)'

    first_author = node.visible_contributors[0]

    return {
        'id': node._id,
        'title': title,
        'firstAuthor': first_author.family_name or first_author.given_name or first_author.full_name,
        'etal': len(node.visible_contributors) > 1,
    }


@must_be_logged_in
def search_node(auth, **kwargs):
    """

    """
    # Get arguments
    node = Node.load(request.json.get('nodeId'))
    include_public = request.json.get('includePublic')
    size = float(request.json.get('size', '5').strip())
    page = request.json.get('page', 0)
    query = request.json.get('query', '').strip()

    start = (page * size)
    if not query:
        return {'nodes': []}

    # Build ODM query
    title_query = Q('title', 'icontains', query)
    not_deleted_query = Q('is_deleted', 'eq', False)
    visibility_query = Q('contributors', 'eq', auth.user)
    no_folders_query = Q('is_folder', 'eq', False)
    if include_public:
        visibility_query = visibility_query | Q('is_public', 'eq', True)
    odm_query = title_query & not_deleted_query & visibility_query & no_folders_query

    # Exclude current node from query if provided
    if node:
        nin = [node._id] + node.node_ids
        odm_query = (
            odm_query &
            Q('_id', 'nin', nin)
        )

    nodes = Node.find(odm_query)
    count = nodes.count()
    pages = math.ceil(count / size)
    validate_page_num(page, pages)

    return {
        'nodes': [
            _serialize_node_search(each)
            for each in islice(nodes, start, start + size)
            if each.contributors
        ],
        'total': count,
        'pages': pages,
        'page': page
    }


def _add_pointers(node, pointers, auth):
    """

    :param Node node: Node to which pointers will be added
    :param list pointers: Nodes to add as pointers

    """
    added = False
    for pointer in pointers:
        node.add_pointer(pointer, auth, save=False)
        added = True

    if added:
        node.save()


@collect_auth
def move_pointers(auth):
    """Move pointer from one node to another node.

    """

    from_node_id = request.json.get('fromNodeId')
    to_node_id = request.json.get('toNodeId')
    pointers_to_move = request.json.get('pointerIds')

    if from_node_id is None or to_node_id is None or pointers_to_move is None:
        raise HTTPError(http.BAD_REQUEST)

    from_node = Node.load(from_node_id)
    to_node = Node.load(to_node_id)

    if to_node is None or from_node is None:
        raise HTTPError(http.BAD_REQUEST)

    for pointer_to_move in pointers_to_move:
        pointer_id = from_node.pointing_at(pointer_to_move)
        pointer_node = Node.load(pointer_to_move)

        pointer = Pointer.load(pointer_id)
        if pointer is None:
            raise HTTPError(http.BAD_REQUEST)

        try:
            from_node.rm_pointer(pointer, auth=auth)
        except ValueError:
            raise HTTPError(http.BAD_REQUEST)

        from_node.save()
        try:
            _add_pointers(to_node, [pointer_node], auth)
        except ValueError:
            raise HTTPError(http.BAD_REQUEST)

    return {}, 200, None


@collect_auth
def add_pointer(auth):
    """Add a single pointer to a node using only JSON parameters

    """
    to_node_id = request.json.get('toNodeID')
    pointer_to_move = request.json.get('pointerID')

    if not (to_node_id and pointer_to_move):
        raise HTTPError(http.BAD_REQUEST)

    pointer = Node.load(pointer_to_move)
    to_node = Node.load(to_node_id)
    try:
        _add_pointers(to_node, [pointer], auth)
    except ValueError:
        raise HTTPError(http.BAD_REQUEST)


@must_have_permission(WRITE)
@must_not_be_registration
def add_pointers(auth, node, **kwargs):
    """Add pointers to a node.

    """
    node_ids = request.json.get('nodeIds')

    if not node_ids:
        raise HTTPError(http.BAD_REQUEST)

    nodes = [
        Node.load(node_id)
        for node_id in node_ids
    ]

    try:
        _add_pointers(node, nodes, auth)
    except ValueError:
        raise HTTPError(http.BAD_REQUEST)

    return {}


@must_have_permission(WRITE)
@must_not_be_registration
def remove_pointer(auth, node, **kwargs):
    """Remove a pointer from a node, raising a 400 if the pointer is not
    in `node.nodes`.

    """
    # TODO: since these a delete request, shouldn't use request body. put pointer
    # id in the URL instead
    pointer_id = request.json.get('pointerId')
    if pointer_id is None:
        raise HTTPError(http.BAD_REQUEST)

    pointer = Pointer.load(pointer_id)
    if pointer is None:
        raise HTTPError(http.BAD_REQUEST)

    try:
        node.rm_pointer(pointer, auth=auth)
    except ValueError:
        raise HTTPError(http.BAD_REQUEST)

    node.save()


@must_be_valid_project  # injects project
@must_have_permission(WRITE)
@must_not_be_registration
def remove_pointer_from_folder(auth, node, pointer_id, **kwargs):
    """Remove a pointer from a node, raising a 400 if the pointer is not
    in `node.nodes`.

    """
    if pointer_id is None:
        raise HTTPError(http.BAD_REQUEST)

    pointer_id = node.pointing_at(pointer_id)

    pointer = Pointer.load(pointer_id)

    if pointer is None:
        raise HTTPError(http.BAD_REQUEST)

    try:
        node.rm_pointer(pointer, auth=auth)
    except ValueError:
        raise HTTPError(http.BAD_REQUEST)

    node.save()


@must_be_valid_project  # injects project
@must_have_permission(WRITE)
@must_not_be_registration
def remove_pointers_from_folder(auth, node, **kwargs):
    """Remove multiple pointers from a node, raising a 400 if the pointer is not
    in `node.nodes`.
    """
    pointer_ids = request.json.get('pointerIds')

    if pointer_ids is None:
        raise HTTPError(http.BAD_REQUEST)

    for pointer_id in pointer_ids:
        pointer_id = node.pointing_at(pointer_id)

        pointer = Pointer.load(pointer_id)

        if pointer is None:
            raise HTTPError(http.BAD_REQUEST)

        try:
            node.rm_pointer(pointer, auth=auth)
        except ValueError:
            raise HTTPError(http.BAD_REQUEST)

    node.save()


@must_have_permission(WRITE)
@must_not_be_registration
def fork_pointer(auth, node, **kwargs):
    """Fork a pointer. Raises BAD_REQUEST if pointer not provided, not found,
    or not present in `nodes`.

    """
    pointer_id = request.json.get('pointerId')
    pointer = Pointer.load(pointer_id)

    if pointer is None:
        # TODO: Change this to 404?
        raise HTTPError(http.BAD_REQUEST)

    try:
        node.fork_pointer(pointer, auth=auth, save=True)
    except ValueError:
        raise HTTPError(http.BAD_REQUEST)


def abbrev_authors(node):
    lead_author = node.visible_contributors[0]
    ret = lead_author.family_name or lead_author.given_name or lead_author.fullname
    if len(node.visible_contributor_ids) > 1:
        ret += ' et al.'
    return ret


def serialize_pointer(pointer, auth):
    node = get_pointer_parent(pointer)
    if node.can_view(auth):
        return {
            'id': node._id,
            'url': node.url,
            'title': node.title,
            'authorShort': abbrev_authors(node),
        }
    return {
        'url': None,
        'title': 'Private Component',
        'authorShort': 'Private Author(s)',
    }


@must_be_contributor_or_public
def get_pointed(auth, node, **kwargs):
    """View that returns the pointers for a project."""
    # exclude folders
    return {'pointed': [
        serialize_pointer(each, auth)
        for each in node.pointed
        if not get_pointer_parent(each).is_folder
    ]}
