# -*- coding: utf-8 -*-
import os
import logging
import httplib as http
import math
from collections import defaultdict
from itertools import islice

from flask import request
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db.models import Q, OuterRef, Exists, Subquery
import waffle

from framework import status
from framework.utils import iso8601format
from framework.flask import redirect  # VOL-aware redirect
from framework.auth.decorators import must_be_logged_in, collect_auth
from website.ember_osf_web.decorators import ember_flag_is_active, storage_i18n_flag_active
from framework.exceptions import HTTPError
from osf.models.nodelog import NodeLog
from osf.utils.functional import rapply
from osf import features

from website import language

from website.util import rubeus
from website.ember_osf_web.views import use_ember_app
from website.exceptions import NodeStateError
from website.project import new_node, new_private_link
from website.project.decorators import (
    must_be_contributor_or_public_but_not_anonymized,
    must_be_contributor_or_public,
    must_be_valid_project,
    must_have_permission,
    must_not_be_registration,
    must_not_be_retracted_registration,
)
from website.tokens import process_token_or_pass
from website.util.rubeus import collect_addon_js
from website.project.model import has_anonymous_link, NodeUpdateError, validate_title
from website.project.forms import NewNodeForm
from website.project.metadata.utils import serialize_meta_schemas
from osf.models import AbstractNode, Collection, Guid, PrivateLink, Contributor, Node, NodeRelation, Preprint
from addons.wiki.models import WikiPage
from osf.models.contributor import get_contributor_permissions
from osf.models.licenses import serialize_node_license_record
from osf.utils.sanitize import strip_html
from osf.utils.permissions import ADMIN, READ, WRITE, CREATOR_PERMISSIONS
from website import settings
from website.views import find_bookmark_collection, validate_page_num
from website.views import serialize_node_summary, get_storage_region_list
from website.profile import utils
from addons.mendeley.provider import MendeleyCitationsProvider
from addons.zotero.provider import ZoteroCitationsProvider
from addons.wiki.utils import serialize_wiki_widget
from addons.wiki.models import WikiVersion
from addons.dataverse.utils import serialize_dataverse_widget
from addons.forward.utils import serialize_forward_widget

r_strip_html = lambda collection: rapply(collection, strip_html)
logger = logging.getLogger(__name__)

@must_be_valid_project
@must_have_permission(WRITE)
@must_not_be_registration
def edit_node(auth, node, **kwargs):
    post_data = request.json
    edited_field = post_data.get('name')
    value = post_data.get('value', '')

    new_val = None
    if edited_field == 'title':
        try:
            node.set_title(value, auth=auth)
        except ValidationError as e:
            raise HTTPError(
                http.BAD_REQUEST,
                data=dict(message_long=e.message)
            )
        new_val = node.title
    elif edited_field == 'description':
        node.set_description(value, auth=auth)
        new_val = node.description
    elif edited_field == 'category':
        node.category = new_val = value

    try:
        node.save()
    except ValidationError as e:
        raise HTTPError(
            http.BAD_REQUEST,
            data=dict(message_long=e.message)
        )
    return {
        'status': 'success',
        'newValue': new_val  # Used by x-editable  widget to reflect changes made by sanitizer
    }


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
        original_node = AbstractNode.load(template)
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
        except ValidationError as e:
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
        except ValidationError as e:
            raise HTTPError(
                http.BAD_REQUEST,
                data=dict(message_long=e.message)
            )
        redirect_url = node.url
        message = (
            'Your component was created successfully. You can keep working on the project page below, '
            'or go to the new <u><a href={component_url}>component</a></u>.'
        ).format(component_url=new_component.url)
        if form.inherit_contributors.data and node.has_permission(user, WRITE):
            for contributor in node.contributors:
                perm = CREATOR_PERMISSIONS if contributor._id == user._id else node.get_permissions(contributor)
                if contributor._id == user._id and not contributor.is_registered:
                    new_component.add_unregistered_contributor(
                        fullname=contributor.fullname, email=contributor.email,
                        permissions=perm, auth=auth, existing_user=contributor
                    )
                else:
                    new_component.add_contributor(contributor, permissions=perm, auth=auth)

            new_component.save()
            redirect_url = new_component.url + 'contributors/'
            message = (
                'Your component was created successfully. You can edit the contributor permissions below, '
                'work on your <u><a href={component_url}>component</a></u> or return to the <u> '
                '<a href="{project_url}">project page</a></u>.'
            ).format(component_url=new_component.url, project_url=node.url)
        status.push_status_message(message, kind='info', trust=True)

        return {
            'status': 'success',
        }, 201, None, redirect_url
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

    return {'prompts': prompts, 'isRegistration': node.is_registration}


@must_be_valid_project
@must_be_contributor_or_public_but_not_anonymized
@must_not_be_registration
@ember_flag_is_active(features.EMBER_PROJECT_REGISTRATIONS)
def node_registrations(auth, node, **kwargs):
    return _view_project(node, auth, primary=True, embed_registrations=True)

@must_be_valid_project
@must_be_contributor_or_public_but_not_anonymized
@must_not_be_retracted_registration
def node_forks(auth, node, **kwargs):
    if request.path.startswith('/project/'):
        return redirect('/' + node._id + '/forks/')
    return use_ember_app()

@must_be_valid_project
@must_not_be_retracted_registration
@must_be_logged_in
@must_have_permission(READ)
@ember_flag_is_active(features.EMBER_PROJECT_SETTINGS)
def node_setting(auth, node, **kwargs):
    if node.is_registration and waffle.flag_is_active(request, features.EMBER_REGISTRIES_DETAIL_PAGE):
        # Registration settings page obviated during redesign
        return redirect(node.url)
    auth.user.update_affiliated_institutions_by_email_domain()
    auth.user.save()
    ret = _view_project(node, auth, primary=True)

    ret['include_wiki_settings'] = WikiPage.objects.include_wiki_settings(node)
    ret['wiki_enabled'] = 'wiki' in node.get_addon_names()

    ret['comments'] = {
        'level': node.comment_level,
    }

    addon_settings = {}
    for addon in ['forward']:
        addon_config = apps.get_app_config('addons_{}'.format(addon))
        config = addon_config.to_json()
        config['template_lookup'] = addon_config.template_lookup
        config['addon_icon_url'] = addon_config.icon_url
        config['node_settings_template'] = os.path.basename(addon_config.node_settings_template)
        addon_settings[addon] = config

    ret['addon_settings'] = addon_settings

    ret['categories'] = settings.NODE_CATEGORY_MAP
    ret['categories'].update({
        'project': 'Project'
    })

    return ret

@must_be_valid_project
@must_not_be_registration
@must_be_logged_in
@must_have_permission(WRITE)
def node_addons(auth, node, **kwargs):

    ret = _view_project(node, auth, primary=True)

    addon_settings = serialize_addons(node, auth)

    ret['addon_capabilities'] = settings.ADDON_CAPABILITIES

    # If an addon is default you cannot connect/disconnect so we don't have to load it.
    ret['addon_settings'] = [addon for addon in addon_settings]

    # Addons can have multiple categories, but we only want a set of unique ones being used.
    ret['addon_categories'] = set([item for addon in addon_settings for item in addon['categories']])

    # The page only needs to load enabled addons and it refreshes when a new addon is being enabled.
    ret['addon_js'] = collect_node_config_js([addon for addon in addon_settings if addon['enabled']])

    return ret


def serialize_addons(node, auth):

    addon_settings = []
    addons_available = [addon for addon in settings.ADDONS_AVAILABLE
                        if addon not in settings.SYSTEM_ADDED_ADDONS['node']
                        and addon.short_name not in ('wiki', 'forward', 'twofactor')]

    for addon in addons_available:
        addon_config = apps.get_app_config('addons_{}'.format(addon.short_name))
        config = addon_config.to_json()
        config['template_lookup'] = addon_config.template_lookup
        config['addon_icon_url'] = addon_config.icon_url
        config['node_settings_template'] = os.path.basename(addon_config.node_settings_template)
        config['addon_short_name'] = addon.short_name
        config['addon_full_name'] = addon.full_name
        config['categories'] = addon.categories
        config['enabled'] = node.has_addon(addon.short_name)
        config['default'] = addon.short_name in settings.ADDONS_DEFAULT

        if node.has_addon(addon.short_name):
            node_json = node.get_addon(addon.short_name).to_json(auth.user)
            config.update(node_json)

        addon_settings.append(config)

    addon_settings = sorted(addon_settings, key=lambda addon: addon['full_name'].lower())

    return addon_settings

def collect_node_config_js(addons):
    """Collect webpack bundles for each of the addons' node-cfg.js modules. Return
    the URLs for each of the JS modules to be included on the node addons config page.

    :param list addons: List of node's addon config records.
    """
    js_modules = []
    for addon in addons:
        source_path = os.path.join(
            settings.ADDON_PATH,
            addon['short_name'],
            'static',
            'node-cfg.js',
        )
        if os.path.exists(source_path):
            asset_path = os.path.join(
                '/',
                'static',
                'public',
                'js',
                addon['short_name'],
                'node-cfg.js',
            )
            js_modules.append(asset_path)

    return js_modules


@must_have_permission(WRITE)
@must_not_be_registration
def node_choose_addons(auth, node, **kwargs):
    node.config_addons(request.json, auth)


@must_be_valid_project
@must_not_be_retracted_registration
@must_have_permission(READ)
@ember_flag_is_active(features.EMBER_PROJECT_CONTRIBUTORS)
def node_contributors(auth, node, **kwargs):
    ret = _view_project(node, auth, primary=True)
    ret['contributors'] = utils.serialize_contributors(node.contributors, node)
    ret['access_requests'] = utils.serialize_access_requests(node)
    ret['adminContributors'] = utils.serialize_contributors(node.parent_admin_contributors, node, admin=True)
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

@must_have_permission(ADMIN)
@must_not_be_registration
def configure_requests(node, **kwargs):
    access_requests_enabled = request.get_json().get('accessRequestsEnabled')
    auth = kwargs.get('auth', None)
    node.set_access_requests_enabled(access_requests_enabled, auth, save=True)
    return {'access_requests_enabled': access_requests_enabled}, 200


##############################################################################
# View Project
##############################################################################

@process_token_or_pass
@must_be_valid_project(retractions_valid=True)
@must_be_contributor_or_public
@ember_flag_is_active(features.EMBER_PROJECT_DETAIL)
def view_project(auth, node, **kwargs):
    primary = '/api/v1' not in request.path
    ret = _view_project(node, auth,
                        primary=primary,
                        embed_contributors=True,
                        embed_descendants=True
                        )

    ret['addon_capabilities'] = settings.ADDON_CAPABILITIES
    # Collect the URIs to the static assets for addons that have widgets
    ret['addon_widget_js'] = list(collect_addon_js(
        node,
        filename='widget-cfg.js',
        config_entry='widget'
    ))
    ret.update(rubeus.collect_addon_assets(node))

    access_request = node.requests.filter(creator=auth.user).exclude(machine_state='accepted')
    ret['user']['access_request_state'] = access_request.get().machine_state if access_request else None

    addons_widget_data = {
        'wiki': None,
        'mendeley': None,
        'zotero': None,
        'forward': None,
        'dataverse': None
    }

    if 'wiki' in ret['addons']:
        addons_widget_data['wiki'] = serialize_wiki_widget(node)

    if 'dataverse' in ret['addons']:
        addons_widget_data['dataverse'] = serialize_dataverse_widget(node)

    if 'forward' in ret['addons']:
        addons_widget_data['forward'] = serialize_forward_widget(node)

    if 'zotero' in ret['addons']:
        node_addon = node.get_addon('zotero')
        zotero_widget_data = ZoteroCitationsProvider().widget(node_addon)
        addons_widget_data['zotero'] = zotero_widget_data

    if 'mendeley' in ret['addons']:
        node_addon = node.get_addon('mendeley')
        mendeley_widget_data = MendeleyCitationsProvider().widget(node_addon)
        addons_widget_data['mendeley'] = mendeley_widget_data

    ret.update({'addons_widget_data': addons_widget_data})
    return ret

# Reorder components
@must_be_valid_project
@must_not_be_registration
@must_have_permission(WRITE)
def project_reorder_components(node, **kwargs):
    """Reorders the components in a project's component list.

    :param-json list new_list: List of strings that include node GUIDs.
    """
    ordered_guids = request.get_json().get('new_list', [])
    node_relations = (
        node.node_relations
            .select_related('child')
            .filter(child__is_deleted=False)
    )
    deleted_node_relation_ids = list(
        node.node_relations.select_related('child')
        .filter(child__is_deleted=True)
        .values_list('pk', flat=True)
    )

    if len(ordered_guids) > len(node_relations):
        raise HTTPError(http.BAD_REQUEST, data=dict(message_long='Too many node IDs'))

    # Ordered NodeRelation pks, sorted according the order of guids passed in the request payload
    new_node_relation_ids = [
        each.id for each in sorted(node_relations,
                                   key=lambda nr: ordered_guids.index(nr.child._id))
    ]

    if len(node_relations) == len(ordered_guids):
        node.set_noderelation_order(new_node_relation_ids + deleted_node_relation_ids)
        node.save()
        return {'nodes': ordered_guids}

    logger.error('Got invalid node list in reorder components')
    raise HTTPError(http.BAD_REQUEST)

@must_be_valid_project
@must_be_contributor_or_public
@must_not_be_retracted_registration
def project_statistics(auth, node, **kwargs):
    if request.path.startswith('/project/'):
        return redirect('/' + node._id + '/analytics/')
    return use_ember_app()


###############################################################################
# Make Private/Public
###############################################################################

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
            message_long=str(e)
        ))

    return {
        'status': 'success',
        'permissions': permissions,
    }


@must_be_valid_project
@must_not_be_registration
@must_have_permission(WRITE)
def update_node(auth, node, **kwargs):
    # in node.update() method there is a key list node.WRITABLE_WHITELIST only allow user to modify
    # category, title, and description which can be edited by write permission contributor
    data = r_strip_html(request.get_json())
    try:
        updated_field_names = node.update(data, auth=auth)
    except NodeUpdateError as e:
        raise HTTPError(400, data=dict(
            message_short="Failed to update attribute '{0}'".format(e.key),
            message_long=e.reason
        ))
    # Need to cast tags to a string to make them JSON-serialiable
    updated_fields_dict = {
        key: getattr(node, key) if key != 'tags' else [str(tag) for tag in node.tags]
        for key in updated_field_names
        if key != 'logs' and key != 'modified' and key != 'last_logged'
    }
    return {'updated_fields': updated_fields_dict}

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
                'message_long': 'Could not delete component: ' + str(e)
            },
        )
    node.save()

    message = '{} has been successfully deleted.'.format(
        node.project_or_component.capitalize()
    )
    id = '{}_deleted'.format(node.project_or_component)
    status.push_status_message(message, kind='success', trust=False, id=id)
    parent = node.parent_node
    if parent and parent.can_view(auth):
        redirect_url = node.parent_node.url
    else:
        redirect_url = '/dashboard/'

    return {
        'url': redirect_url,
    }


@must_be_valid_project
@must_have_permission(ADMIN)
def remove_private_link(*args, **kwargs):
    link_id = request.json['private_link_id']

    try:
        link = PrivateLink.objects.get(_id=link_id)
    except PrivateLink.DoesNotExist:
        raise HTTPError(http.NOT_FOUND)

    link.is_deleted = True
    link.save()

    for node in link.nodes.all():
        log_dict = {
            'project': node.parent_id,
            'node': node._id,
            'user': kwargs.get('auth').user._id,
            'anonymous_link': link.anonymous,
        }

        node.add_log(
            NodeLog.VIEW_ONLY_LINK_REMOVED,
            log_dict,
            auth=kwargs.get('auth', None)
        )

# TODO: Split into separate functions
def _render_addons(addons):

    widgets = {}
    configs = {}
    js = []
    css = []

    for addon in addons:
        configs[addon.config.short_name] = addon.config.to_json()
        js.extend(addon.config.include_js.get('widget', []))
        css.extend(addon.config.include_css.get('widget', []))

        js.extend(addon.config.include_js.get('files', []))
        css.extend(addon.config.include_css.get('files', []))

    return widgets, configs, js, css


def _should_show_wiki_widget(node, contributor):
    has_wiki = bool(node.get_addon('wiki'))
    wiki_page = WikiVersion.objects.get_for_node(node, 'home')

    if contributor and contributor.write and not node.is_registration:
        return has_wiki
    else:
        return has_wiki and wiki_page and wiki_page.html(node)


def _view_project(node, auth, primary=False,
                  embed_contributors=False, embed_descendants=False,
                  embed_registrations=False, embed_forks=False):
    """Build a JSON object containing everything needed to render
    project.view.mako.
    """
    node = AbstractNode.objects.filter(pk=node.pk).include('contributor__user__guids').get()
    user = auth.user

    try:
        contributor = node.contributor_set.get(user=user)
    except Contributor.DoesNotExist:
        contributor = None

    parent = node.find_readable_antecedent(auth)
    if user:
        bookmark_collection = find_bookmark_collection(user)
        bookmark_collection_id = bookmark_collection._id
        in_bookmark_collection = bookmark_collection.guid_links.filter(_id=node._id).exists()
    else:
        in_bookmark_collection = False
        bookmark_collection_id = ''

    view_only_link = auth.private_key or request.args.get('view_only', '').strip('/')
    anonymous = has_anonymous_link(node, auth)
    addons = list(node.get_addons())
    widgets, configs, js, css = _render_addons(addons)
    redirect_url = node.url + '?view_only=None'

    disapproval_link = ''
    if (node.is_pending_registration and node.has_permission(user, ADMIN)):
        disapproval_link = node.root.registration_approval.stashed_urls.get(user._id, {}).get('reject', '')

    if (node.is_pending_embargo and node.has_permission(user, ADMIN)):
        disapproval_link = node.root.embargo.stashed_urls.get(user._id, {}).get('reject', '')

    # Before page load callback; skip if not primary call
    if primary:
        for addon in addons:
            messages = addon.before_page_load(node, user) or []
            for message in messages:
                status.push_status_message(message, kind='info', dismissible=False, trust=True)
    NodeRelation = apps.get_model('osf.NodeRelation')

    is_registration = node.is_registration
    data = {
        'node': {
            'disapproval_link': disapproval_link,
            'id': node._primary_key,
            'title': node.title,
            'category': node.category_display,
            'category_short': node.category,
            'node_type': node.project_or_component,
            'description': node.description or '',
            'license': serialize_node_license_record(node.license),
            'url': node.url,
            'api_url': node.api_url,
            'absolute_url': node.absolute_url,
            'redirect_url': redirect_url,
            'display_absolute_url': node.display_absolute_url,
            'update_url': node.api_url_for('update_node'),
            'in_dashboard': in_bookmark_collection,
            'is_public': node.is_public,
            'is_archiving': node.archiving,
            'date_created': iso8601format(node.created),
            'date_modified': iso8601format(node.last_logged) if node.last_logged else '',
            'tags': list(node.tags.filter(system=False).values_list('name', flat=True)),
            'children': node.nodes_active.exists(),
            'child_exists': Node.objects.get_children(node, active=True).exists(),
            'is_supplemental_project': node.has_linked_published_preprints,
            'is_registration': is_registration,
            'is_pending_registration': node.is_pending_registration if is_registration else False,
            'is_retracted': node.is_retracted if is_registration else False,
            'is_pending_retraction': node.is_pending_retraction if is_registration else False,
            'retracted_justification': getattr(node.retraction, 'justification', None) if is_registration else None,
            'date_retracted': iso8601format(getattr(node.retraction, 'date_retracted', None)) if is_registration else '',
            'embargo_end_date': node.embargo_end_date.strftime('%A, %b %d, %Y') if is_registration and node.embargo_end_date else '',
            'is_pending_embargo': node.is_pending_embargo if is_registration else False,
            'is_embargoed': node.is_embargoed if is_registration else False,
            'is_pending_embargo_termination': is_registration and node.is_pending_embargo_termination,
            'registered_from_url': node.registered_from.url if is_registration else '',
            'registered_date': iso8601format(node.registered_date) if is_registration else '',
            'root_id': node.root._id if node.root else None,
            'registered_meta': node.registered_meta,
            'registered_schemas': serialize_meta_schemas(list(node.registered_schema.all())) if is_registration else False,
            'is_fork': node.is_fork,
            'is_collected': node.is_collected,
            'collections': serialize_collections(node.collecting_metadata_list, auth),
            'forked_from_id': node.forked_from._primary_key if node.is_fork else '',
            'forked_from_display_absolute_url': node.forked_from.display_absolute_url if node.is_fork else '',
            'forked_date': iso8601format(node.forked_date) if node.is_fork else '',
            'fork_count': node.forks.exclude(type='osf.registration').filter(is_deleted=False).count(),
            'private_links': [x.to_json() for x in node.private_links_active],
            'link': view_only_link,
            'templated_count': node.templated_list.count(),
            'linked_nodes_count': NodeRelation.objects.filter(child=node, is_node_link=True).exclude(parent__type='osf.collection').count(),
            'anonymous': anonymous,
            'comment_level': node.comment_level,
            'has_comments': node.comment_set.exists(),
            'identifiers': {
                'doi': node.get_identifier_value('doi'),
                'ark': node.get_identifier_value('ark'),
            },
            'visible_preprints': serialize_preprints(node, user),
            'institutions': get_affiliated_institutions(node) if node else [],
            'has_draft_registrations': node.has_active_draft_registrations,
            'access_requests_enabled': node.access_requests_enabled,
            'storage_location': node.osfstorage_region.name,
            'waterbutler_url': node.osfstorage_region.waterbutler_url,
            'mfr_url': node.osfstorage_region.mfr_url
        },
        'parent_node': {
            'exists': parent is not None,
            'id': parent._primary_key if parent else '',
            'title': parent.title if parent else '',
            'category': parent.category_display if parent else '',
            'url': parent.url if parent else '',
            'api_url': parent.api_url if parent else '',
            'absolute_url': parent.absolute_url if parent else '',
            'registrations_url': parent.web_url_for('node_registrations', _guid=True) if parent else '',
            'is_public': parent.is_public if parent else '',
            'is_contributor': parent.is_contributor(user) if parent else '',
            'can_view': parent.can_view(auth) if parent else False,
        },
        'user': {
            'is_contributor': bool(contributor),
            'is_admin': bool(contributor) and contributor.admin,
            'is_admin_parent': parent.is_admin_parent(user) if parent else False,
            'can_edit': bool(contributor) and contributor.write and not node.is_registration,
            'can_edit_tags': bool(contributor) and contributor.write,
            'has_read_permissions': node.has_permission(user, READ),
            'permissions': get_contributor_permissions(contributor, as_list=True) if contributor else [],
            'id': user._id if user else None,
            'username': user.username if user else None,
            'fullname': user.fullname if user else '',
            'can_comment': bool(contributor) or node.can_comment(auth),
            'show_wiki_widget': _should_show_wiki_widget(node, contributor),
            'dashboard_id': bookmark_collection_id,
            'institutions': get_affiliated_institutions(user) if user else [],
        },
        # TODO: Namespace with nested dicts
        'addons_enabled': [each.short_name for each in addons],
        'addons': configs,
        'addon_widgets': widgets,
        'addon_widget_js': js,
        'addon_widget_css': css,
        'node_categories': [
            {'value': key, 'display_name': value}
            for key, value in settings.NODE_CATEGORY_MAP.items()
        ]
    }

    # Default should be at top of list for UI and for the project overview page the default region
    # for a component is that of the it's parent node.
    region_list = get_storage_region_list(user, node=node)

    data.update({'storage_regions': region_list})
    data.update({'storage_flag_is_active': storage_i18n_flag_active()})

    if embed_contributors and not anonymous:
        data['node']['contributors'] = utils.serialize_visible_contributors(node)
    else:
        data['node']['contributors'] = list(node.contributors.values_list('guids___id', flat=True))
    if embed_descendants:
        descendants, all_readable = _get_readable_descendants(auth=auth, node=node)
        data['user']['can_sort'] = all_readable
        data['node']['descendants'] = [
            serialize_node_summary(node=each, auth=auth, primary=not node.has_node_link_to(each), show_path=False)
            for each in descendants
        ]
    if embed_registrations:
        data['node']['registrations'] = [
            serialize_node_summary(node=each, auth=auth, show_path=False)
            for each in node.registrations_all.order_by('-registered_date').exclude(is_deleted=True)
        ]
    if embed_forks:
        data['node']['forks'] = [
            serialize_node_summary(node=each, auth=auth, show_path=False)
            for each in node.forks.exclude(type='osf.registration').exclude(is_deleted=True).order_by('-forked_date')
        ]
    return data

def get_affiliated_institutions(obj):
    ret = []
    for institution in obj.affiliated_institutions.all():
        ret.append({
            'name': institution.name,
            'logo_path': institution.logo_path,
            'logo_path_rounded_corners': institution.logo_path_rounded_corners,
            'id': institution._id,
        })
    return ret

def serialize_collections(cgms, auth):
    return [{
        'title': cgm.collection.title,
        'name': cgm.collection.provider.name,
        'url': '/collections/{}/'.format(cgm.collection.provider._id),
        'status': cgm.status,
        'type': cgm.collected_type,
        'issue': cgm.issue,
        'volume': cgm.volume,
        'program_area': cgm.program_area,
        'subjects': list(cgm.subjects.values_list('text', flat=True)),
        'is_public': cgm.collection.is_public,
        'logo': cgm.collection.provider.get_asset_url('favicon')
    } for cgm in cgms if cgm.collection.provider and (cgm.collection.is_public or
        (auth.user and auth.user.has_perm('read_collection', cgm.collection)))]

def serialize_preprints(node, user):
    return [
        {
            'title': preprint.title,
            'is_moderated': preprint.provider.reviews_workflow,
            'is_withdrawn': preprint.date_withdrawn is not None,
            'state': preprint.machine_state,
            'word': preprint.provider.preprint_word,
            'provider': {'name': 'OSF Preprints' if preprint.provider.name == 'Open Science Framework' else preprint.provider.name, 'workflow': preprint.provider.reviews_workflow},
            'url': preprint.url,
            'absolute_url': preprint.absolute_url
        } for preprint in Preprint.objects.can_view(base_queryset=node.preprints, user=user).filter(date_withdrawn__isnull=True)
    ]


def serialize_children(child_list, nested, indent=0):
    """
    Returns the serialized representation of a list of child nodes.

    This is a helper function for _get_children and as such it does not
    redundantly check permissions.
    """
    results = []
    for child in child_list:
        results.append({
            'id': child._id,
            'title': child.title,
            'is_public': child.is_public,
            'parent_id': child.parentnode_id,
            'indent': indent
        })
        if child._id in nested.keys():
            results.extend(serialize_children(nested.get(child._id), nested, indent + 1))
    return results

def _get_children(node, auth):
    """
    Returns the serialized representation of the given node and all of its children
    for which the given user has ADMIN permission.
    """
    is_admin = Contributor.objects.filter(node=OuterRef('pk'), admin=True, user=auth.user)
    parent_node_sqs = NodeRelation.objects.filter(child=OuterRef('pk'), is_node_link=False).values('parent__guids___id')
    children = (Node.objects.get_children(node)
                .filter(is_deleted=False)
                .annotate(parentnode_id=Subquery(parent_node_sqs[:1]))
                .annotate(has_admin_perm=Exists(is_admin))
                .filter(has_admin_perm=True))

    nested = defaultdict(list)
    for child in children:
        nested[child.parentnode_id].append(child)

    return serialize_children(nested[node._id], nested)


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
@must_have_permission(ADMIN)
def get_editable_children(auth, node, **kwargs):

    children = _get_children(node, auth)

    return {
        'node': {'id': node._id, 'title': node.title, 'is_public': node.is_public},
        'children': children,
    }


@must_be_valid_project
def get_recent_logs(node, **kwargs):
    logs = list(reversed(node.logs._to_primary_keys()))[:3]
    return {'logs': logs}


def _get_readable_descendants(auth, node, permission=None):
    descendants = []
    all_readable = True
    for child in node.get_nodes(is_deleted=False):
        if permission:
            perm = permission.lower().strip()
            if not child.has_permission(auth.user, perm):
                all_readable = False
                continue
        # User can view child
        if child.can_view(auth):
            descendants.append(child)
        # Child is a node link and user has write permission
        elif node.linked_nodes.filter(id=child.id).exists():
            if node.has_permission(auth.user, 'write'):
                descendants.append(child)
            else:
                all_readable = False
        else:
            all_readable = False
            for descendant in child.find_readable_descendants(auth):
                descendants.append(descendant)
    return descendants, all_readable

def serialize_child_tree(child_list, user, nested):
    """
    Recursively serializes and returns a list of child nodes.

    This is a helper function for node_child_tree and as such it does not
    redundantly check permissions.
    """
    serialized_children = []
    for child in child_list:
        if child.has_read_perm or child.has_permission_on_children(user, READ):
            contributors = [{
                'id': contributor.user._id,
                'is_admin': contributor.admin,
                'is_confirmed': contributor.user.is_confirmed,
                'visible': contributor.visible
            } for contributor in child.contributor_set.all()]

            serialized_children.append({
                'node': {
                    'id': child._id,
                    'url': child.url,
                    'title': child.title,
                    'is_public': child.is_public,
                    'contributors': contributors,
                    'is_admin': child.has_admin_perm,
                    'is_supplemental_project': child.has_linked_published_preprints,
                },
                'user_id': user._id,
                'children': serialize_child_tree(nested.get(child._id), user, nested) if child._id in nested.keys() else [],
                'nodeType': 'project' if not child.parentnode_id else 'component',
                'category': child.category,
                'permissions': {
                    'view': True,
                    'is_admin': child.has_admin_perm
                }
            })

    return sorted(serialized_children, key=lambda k: len(k['children']), reverse=True)

def node_child_tree(user, node):
    """ Returns the serialized representation (for treebeard) of a given node and its children.
    :param user: OSFUser object
    :param node: parent project Node object
    :return: treebeard-formatted data
    """
    serialized_nodes = []

    assert node, '{} is not a valid Node.'.format(node._id)

    is_admin_sqs = Contributor.objects.filter(node=OuterRef('pk'), admin=True, user=user)
    can_read_sqs = Contributor.objects.filter(node=OuterRef('pk'), read=True, user=user)
    parent_node_sqs = NodeRelation.objects.filter(child=OuterRef('pk'), is_node_link=False).values('parent__guids___id')
    children = (Node.objects.get_children(node)
                .filter(is_deleted=False)
                .annotate(parentnode_id=Subquery(parent_node_sqs[:1]))
                .annotate(has_admin_perm=Exists(is_admin_sqs))
                .annotate(has_read_perm=Exists(can_read_sqs))
                .include('contributor__user__guids')
                )

    nested = defaultdict(list)
    for child in children:
        nested[child.parentnode_id].append(child)

    contributors = [{
        'id': contributor.user._id,
        'is_admin': node.has_permission(contributor.user, ADMIN),
        'is_confirmed': contributor.user.is_confirmed,
        'visible': contributor.visible
    } for contributor in node.contributor_set.all().include('user__guids')]

    can_read = node.has_permission(user, READ)
    is_admin = node.has_permission(user, ADMIN)

    if can_read or node.has_permission_on_children(user, READ):
        serialized_nodes.append({
            'node': {
                'id': node._id,
                'url': node.url if can_read else '',
                'title': node.title if can_read else 'Private Project',
                'is_public': node.is_public,
                'contributors': contributors,
                'is_admin': is_admin,
                'is_supplemental_project': node.has_linked_published_preprints,

            },
            'user_id': user._id,
            'children': serialize_child_tree(nested.get(node._id), user, nested) if node._id in nested.keys() else [],
            'kind': 'folder' if not node.parent_node or not node.parent_node.has_permission(user, 'read') else 'node',
            'nodeType': node.project_or_component,
            'category': node.category,
            'permissions': {
                'view': can_read,
                'is_admin': is_admin
            }
        })

    return serialized_nodes

@must_be_logged_in
@must_be_valid_project
def get_node_tree(auth, **kwargs):
    node = kwargs.get('node') or kwargs['project']
    tree = node_child_tree(auth.user, node)
    return tree

@must_be_valid_project
@must_have_permission(ADMIN)
def project_generate_private_link_post(auth, node, **kwargs):
    """ creata a new private link object and add it to the node and its selected children"""

    node_ids = request.json.get('node_ids', [])
    name = request.json.get('name', '')

    anonymous = request.json.get('anonymous', False)

    if node._id not in node_ids:
        node_ids.insert(0, node._id)

    nodes = [AbstractNode.load(node_id) for node_id in node_ids]

    try:
        new_link = new_private_link(
            name=name, user=auth.user, nodes=nodes, anonymous=anonymous
        )
    except ValidationError as e:
        raise HTTPError(
            http.BAD_REQUEST,
            data=dict(message_long=e.message)
        )

    return new_link


@must_be_valid_project
@must_have_permission(ADMIN)
def project_private_link_edit(auth, **kwargs):
    name = request.json.get('value', '')
    try:
        validate_title(name)
    except ValidationError as e:
        message = 'Invalid link name.' if e.message == 'Invalid title.' else e.message
        raise HTTPError(
            http.BAD_REQUEST,
            data=dict(message_long=message)
        )

    private_link_id = request.json.get('pk', '')
    private_link = PrivateLink.load(private_link_id)

    if private_link:
        new_name = strip_html(name)
        private_link.name = new_name
        private_link.save()
        return new_name
    else:
        raise HTTPError(
            http.BAD_REQUEST,
            data=dict(message_long='View-only link not found.')
        )


def _serialize_node_search(node):
    """Serialize a node for use in pointer search.

    :param Node node: Node to serialize
    :return: Dictionary of node data

    """
    data = {
        'id': node._id,
        'title': node.title,
        'etal': len(node.visible_contributors) > 1,
        'isRegistration': node.is_registration
    }
    if node.is_registration:
        data['title'] += ' (registration)'
        data['dateRegistered'] = node.registered_date.isoformat()
    else:
        data['dateCreated'] = node.created.isoformat()
        data['dateModified'] = node.modified.isoformat()

    first_author = node.visible_contributors[0]
    data['firstAuthor'] = first_author.family_name or first_author.given_name or first_author.fullname

    return data


@must_be_logged_in
def search_node(auth, **kwargs):
    """

    """
    # Get arguments
    node = AbstractNode.load(request.json.get('nodeId'))
    include_public = request.json.get('includePublic')
    size = float(request.json.get('size', '5').strip())
    page = request.json.get('page', 0)
    query = request.json.get('query', '').strip()

    start = (page * size)
    if not query:
        return {'nodes': []}

    # Exclude current node from query if provided
    nin = [node.id] + list(node._nodes.values_list('pk', flat=True)) if node else []

    can_view_query = Q(_contributors=auth.user)
    if include_public:
        can_view_query = can_view_query | Q(is_public=True)

    nodes = (AbstractNode.objects
        .filter(
            can_view_query,
            title__icontains=query,
            is_deleted=False)
        .exclude(id__in=nin)
        .exclude(type='osf.collection')
        .exclude(type='osf.quickfilesnode'))

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
        if isinstance(node, Collection):
            node.collect_object(pointer, auth.user)
        else:
            node.add_pointer(pointer, auth, save=False)
        added = True

    if added:
        node.save()


@collect_auth
def add_pointer(auth):
    """Add a single pointer to a node using only JSON parameters

    """
    to_node_id = request.json.get('toNodeID')
    pointer_to_move = request.json.get('pointerID')

    if not (to_node_id and pointer_to_move):
        raise HTTPError(http.BAD_REQUEST)

    pointer = AbstractNode.load(pointer_to_move)
    to_node = Guid.load(to_node_id).referent
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
        AbstractNode.load(node_id)
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

    pointer = AbstractNode.load(pointer_id)
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

    :param Auth auth: Consolidated authorization
    :param Node node: root from which pointer is child
    :return: Fork of node to which nodelink(pointer) points
    """
    NodeRelation = apps.get_model('osf.NodeRelation')

    linked_node_id = request.json.get('nodeId')
    linked_node = AbstractNode.load(linked_node_id)
    pointer = NodeRelation.objects.filter(child=linked_node, is_node_link=True, parent=node).first()

    if pointer is None:
        # TODO: Change this to 404?
        raise HTTPError(http.BAD_REQUEST)

    try:
        fork = node.fork_pointer(pointer, auth=auth, save=True)
    except ValueError:
        raise HTTPError(http.BAD_REQUEST)

    return {
        'data': {
            'node': serialize_node_summary(node=fork, auth=auth, show_path=False)
        }
    }, http.CREATED

def abbrev_authors(node):
    lead_author = node.visible_contributors[0]
    ret = lead_author.family_name or lead_author.given_name or lead_author.fullname
    if node.visible_contributors.count() > 1:
        ret += ' et al.'
    return ret


def serialize_pointer(node, auth):
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
    NodeRelation = apps.get_model('osf.NodeRelation')
    return {'pointed': [
        serialize_pointer(each.parent, auth)
        for each in NodeRelation.objects.filter(child=node, is_node_link=True)
    ]}
