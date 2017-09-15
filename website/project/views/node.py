# -*- coding: utf-8 -*-
import logging
import httplib as http
import math
from itertools import islice

from bs4 import BeautifulSoup
from flask import request
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db.models import Count, Q

from framework import status
from framework.utils import iso8601format
from framework.auth.decorators import must_be_logged_in, collect_auth
from framework.exceptions import HTTPError
from osf.models.nodelog import NodeLog

from website import language

from website.util import paths
from website.util import rubeus
from website.exceptions import NodeStateError
from website.project import new_node, new_private_link
from website.project.decorators import (
    must_be_contributor_or_public_but_not_anonymized,
    must_be_contributor_or_public,
    must_be_valid_project,
    must_have_permission,
    must_not_be_registration,
)
from website.tokens import process_token_or_pass
from website.util.permissions import ADMIN, READ, WRITE, CREATOR_PERMISSIONS
from website.util.rubeus import collect_addon_js
from website.project.model import has_anonymous_link, NodeUpdateError, validate_title
from website.project.forms import NewNodeForm
from website.project.metadata.utils import serialize_meta_schemas
from osf.models import AbstractNode, PrivateLink, Contributor
from osf.models.contributor import get_contributor_permissions
from osf.models.licenses import serialize_node_license_record
from website import settings
from website.views import find_bookmark_collection, validate_page_num
from website.views import serialize_node_summary
from website.profile import utils
from website.util.sanitize import strip_html
from website.util import rapply
from addons.forward.utils import serialize_settings, settings_complete


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

    return {'prompts': prompts}


@must_be_valid_project
@must_be_contributor_or_public_but_not_anonymized
def node_registrations(auth, node, **kwargs):
    return _view_project(node, auth, primary=True, embed_registrations=True)


@must_be_valid_project
@must_be_contributor_or_public_but_not_anonymized
def node_forks(auth, node, **kwargs):
    return _view_project(node, auth, primary=True, embed_forks=True)


@must_be_valid_project
@must_be_logged_in
@must_have_permission(READ)
def node_setting(auth, node, **kwargs):

    auth.user.update_affiliated_institutions_by_email_domain()
    auth.user.save()
    ret = _view_project(node, auth, primary=True)

    addons_enabled = []
    addon_enabled_settings = []

    addons = list(node.get_addons())
    for addon in addons:
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
        and addon.short_name not in settings.SYSTEM_ADDED_ADDONS['node'] and addon.short_name not in ['wiki', 'forward']
    ], key=lambda addon: addon.full_name.lower())

    for addon in settings.ADDONS_AVAILABLE:
        if 'node' in addon.owners and addon.short_name not in settings.SYSTEM_ADDED_ADDONS['node'] and addon.short_name == 'wiki':
            ret['wiki'] = addon
            break

    ret['addons_enabled'] = addons_enabled
    ret['addon_enabled_settings'] = addon_enabled_settings
    ret['addon_capabilities'] = settings.ADDON_CAPABILITIES
    ret['addon_js'] = collect_node_config_js(addons)

    ret['include_wiki_settings'] = node.include_wiki_settings(auth.user)

    ret['comments'] = {
        'level': node.comment_level,
    }

    ret['categories'] = settings.NODE_CATEGORY_MAP
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

@process_token_or_pass
@must_be_valid_project(retractions_valid=True)
@must_be_contributor_or_public
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

    addons_widget_data = {
        'wiki': None,
        'mendeley': None,
        'zotero': None,
        'forward': None,
        'dataverse': None
    }

    if 'wiki' in ret['addons']:
        wiki = node.get_addon('wiki')
        wiki_page = node.get_wiki_page('home')

        # Show "Read more" link if there are multiple pages or has > 400 characters
        more = len(node.wiki_pages_current.keys()) >= 2
        MAX_DISPLAY_LENGTH = 400
        rendered_before_update = False
        if wiki_page and wiki_page.html(node):
            wiki_html = wiki_page.html(node)
            if len(wiki_html) > MAX_DISPLAY_LENGTH:
                wiki_html = BeautifulSoup(wiki_html[:MAX_DISPLAY_LENGTH] + '...', 'html.parser')
                more = True
            else:
                wiki_html = BeautifulSoup(wiki_html)
            rendered_before_update = wiki_page.rendered_before_update
        else:
            wiki_html = None

        wiki_widget_data = {
            'complete': True,
            'wiki_content': unicode(wiki_html) if wiki_html else None,
            'wiki_content_url': node.api_url_for('wiki_page_content', wname='home'),
            'rendered_before_update': rendered_before_update,
            'more': more,
            'include': False,
        }
        wiki_widget_data.update(wiki.config.to_json())
        addons_widget_data['wiki'] = wiki_widget_data

    if 'dataverse' in ret['addons']:
        node_addon = node.get_addon('dataverse')
        widget_url = node.api_url_for('dataverse_get_widget_contents')

        dataverse_widget_data = {
            'complete': node_addon.complete,
            'widget_url': widget_url,
        }
        dataverse_widget_data.update(node_addon.config.to_json())
        addons_widget_data['dataverse'] = dataverse_widget_data

    if 'forward' in ret['addons']:
        node_addon = node.get_addon('forward')
        forward_widget_data = serialize_settings(node_addon)
        forward_widget_data['complete'] = settings_complete(node_addon)
        forward_widget_data.update(node_addon.config.to_json())
        addons_widget_data['forward'] = forward_widget_data

    if 'zotero' in ret['addons']:
        node_addon = node.get_addon('zotero')
        zotero_widget_data = node_addon.config.to_json()
        zotero_widget_data.update({
            'complete': node_addon.complete,
            'list_id': node_addon.list_id,
        })
        addons_widget_data['zotero'] = zotero_widget_data

    if 'mendeley' in ret['addons']:
        node_addon = node.get_addon('mendeley')
        mendeley_widget_data = node_addon.config.to_json()
        mendeley_widget_data.update({
            'complete': node_addon.complete,
            'list_id': node_addon.list_id,
        })
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


##############################################################################


@must_be_valid_project
@must_be_contributor_or_public
def project_statistics(auth, node, **kwargs):
    ret = _view_project(node, auth, primary=True)
    ret['node']['keenio_read_key'] = node.keenio_read_key
    return ret


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
            message_long=e.message
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
        if key != 'logs' and key != 'date_modified'
    }
    node.save()
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
                'message_long': 'Could not delete component: ' + e.message
            },
        )
    node.save()

    message = '{} has been successfully deleted.'.format(
        node.project_or_component.capitalize()
    )
    status.push_status_message(message, kind='success', trust=False)
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
    wiki_page = node.get_wiki_page('home', None)
    if not contributor or not contributor.write:
        return has_wiki and wiki_page and wiki_page.html(node)
    else:
        return has_wiki


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
        in_bookmark_collection = bookmark_collection.linked_nodes.filter(pk=node.pk).exists()
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
            'date_created': iso8601format(node.date_created),
            'date_modified': iso8601format(node.logs.latest().date) if node.logs.exists() else '',
            'tags': list(node.tags.filter(system=False).values_list('name', flat=True)),
            'children': node.nodes_active.exists(),
            'is_registration': is_registration,
            'is_pending_registration': node.is_pending_registration if is_registration else False,
            'is_retracted': node.is_retracted if is_registration else False,
            'is_pending_retraction': node.is_pending_retraction if is_registration else False,
            'retracted_justification': getattr(node.retraction, 'justification', None) if is_registration else None,
            'date_retracted': iso8601format(getattr(node.retraction, 'date_retracted', None)) if is_registration else '',
            'embargo_end_date': node.embargo_end_date.strftime('%A, %b %d, %Y') if is_registration and node.embargo_end_date else '',
            'is_pending_embargo': node.is_pending_embargo if is_registration else False,
            'is_embargoed': node.is_embargoed if is_registration else False,
            'is_pending_embargo_termination': is_registration and node.is_embargoed and (
                node.embargo_termination_approval and
                node.embargo_termination_approval.is_pending_approval
            ),
            'registered_from_url': node.registered_from.url if is_registration else '',
            'registered_date': iso8601format(node.registered_date) if is_registration else '',
            'root_id': node.root._id if node.root else None,
            'registered_meta': node.registered_meta,
            'registered_schemas': serialize_meta_schemas(list(node.registered_schema.all())) if is_registration else False,
            'is_fork': node.is_fork,
            'forked_from_id': node.forked_from._primary_key if node.is_fork else '',
            'forked_from_display_absolute_url': node.forked_from.display_absolute_url if node.is_fork else '',
            'forked_date': iso8601format(node.forked_date) if node.is_fork else '',
            'fork_count': node.forks.filter(is_deleted=False).count(),
            'private_links': [x.to_json() for x in node.private_links_active],
            'link': view_only_link,
            'anonymous': anonymous,
            'comment_level': node.comment_level,
            'has_comments': node.comment_set.exists(),
            'identifiers': {
                'doi': node.get_identifier_value('doi'),
                'ark': node.get_identifier_value('ark'),
            },
            'institutions': get_affiliated_institutions(node) if node else [],
            'has_draft_registrations': node.has_active_draft_registrations,
            'is_preprint': node.is_preprint,
            'is_preprint_orphan': node.is_preprint_orphan,
            'has_published_preprint': node.preprints.filter(is_published=True).exists() if node else False,
            'preprint_file_id': node.preprint_file._id if node.preprint_file else None,
            'preprint_url': node.preprint_url
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
            'can_view': parent.can_view(auth) if parent else False,
        },
        'user': {
            'is_contributor': bool(contributor),
            'is_admin': bool(contributor) and contributor.admin,
            'is_admin_parent': parent.is_admin_parent(user) if parent else False,
            'can_edit': bool(contributor) and contributor.write and not node.is_registration,
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
            for key, value in settings.NODE_CATEGORY_MAP.iteritems()
        ]
    }
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
            for each in node.registrations_all.order_by('-registered_date').exclude(is_deleted=True).annotate(nlogs=Count('logs'))
        ]
    if embed_forks:
        data['node']['forks'] = [
            serialize_node_summary(node=each, auth=auth, show_path=False)
            for each in node.forks.exclude(type='osf.registration').exclude(is_deleted=True).order_by('-forked_date').annotate(nlogs=Count('logs'))
        ]
    return data

def get_affiliated_institutions(obj):
    ret = []
    for institution in obj.affiliated_institutions.all():
        ret.append({
            'name': institution.name,
            'logo_path': institution.logo_path,
            'id': institution._id,
        })
    return ret

def _get_children(node, auth, indent=0):

    children = []

    for child in node.nodes_primary:
        if not child.is_deleted and child.has_permission(auth.user, ADMIN):
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

def node_child_tree(user, nodes):
    """ Format data to test for node privacy settings for use in treebeard.
    :param user: modular odm User object
    :param nodes: list of parent project node objects
    :return: treebeard-formatted data
    """
    items = []

    for node in nodes:
        assert node, '{} is not a valid Node.'.format(node._id)

        can_read = node.has_permission(user, READ)
        can_read_children = node.has_permission_on_children(user, 'read')
        if not can_read and not can_read_children:
            continue

        contributors = []
        for contributor in node.contributors:
            contributors.append({
                'id': contributor._id,
                'is_admin': node.has_permission(contributor, ADMIN),
                'is_confirmed': contributor.is_confirmed
            })

        affiliated_institutions = [{
            'id': affiliated_institution.pk,
            'name': affiliated_institution.name
        } for affiliated_institution in node.affiliated_institutions.all()]

        children = node.get_nodes(**{'is_deleted': False, 'is_node_link': False})
        children_tree = []
        # List project/node if user has at least 'read' permissions (contributor or admin viewer) or if
        # user is contributor on a component of the project/node
        children_tree.extend(node_child_tree(user, children))

        item = {
            'node': {
                'id': node._id,
                'url': node.url if can_read else '',
                'title': node.title if can_read else 'Private Project',
                'is_public': node.is_public,
                'contributors': contributors,
                'visible_contributors': list(node.visible_contributor_ids),
                'is_admin': node.has_permission(user, ADMIN),
                'affiliated_institutions': affiliated_institutions
            },
            'user_id': user._id,
            'children': children_tree,
            'kind': 'folder' if not node.parent_node or not node.parent_node.has_permission(user, 'read') else 'node',
            'nodeType': node.project_or_component,
            'category': node.category,
            'permissions': {
                'view': can_read,
                'is_admin': node.has_permission(user, 'read')
            }
        }

        items.append(item)

    return items


@must_be_logged_in
@must_be_valid_project
def get_node_tree(auth, **kwargs):
    node = kwargs.get('node') or kwargs['project']
    tree = node_child_tree(auth.user, [node])
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
        data['dateCreated'] = node.date_created.isoformat()
        data['dateModified'] = node.date_modified.isoformat()

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
    to_node = AbstractNode.load(to_node_id)
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
    # exclude folders
    return {'pointed': [
        serialize_pointer(each.parent, auth)
        for each in NodeRelation.objects.filter(child=node, is_node_link=True).exclude(parent__type='osf.collection')
    ]}
