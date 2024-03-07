# -*- coding: utf-8 -*-

import os
import re
import gc
import json
import logging
import random
import string
import collections
import unicodedata
import urllib.parse
import requests
from api.base.utils import waterbutler_api_url_for
from addons.wiki.utils import to_mongo_key
from addons.wiki import settings
from addons.wiki import utils as wiki_utils
from addons.wiki.models import WikiPage, WikiVersion, WikiImportTask
from addons.wiki import tasks
from addons.wiki.exceptions import ImportTaskAborted
from osf.management.commands.import_EGAP import get_creator_auth_header
from osf.models.files import BaseFileNode
from rest_framework import status as http_status

from celery.result import AsyncResult
from celery.contrib.abortable import AbortableAsyncResult
from flask import request
from django.db.models.expressions import F
from django_bulk_update.helper import bulk_update
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from framework.exceptions import HTTPError
from framework.auth.utils import privacy_info_handle
from framework.auth.decorators import must_be_logged_in
from framework.auth.core import get_current_user_id
from framework.flask import redirect

from framework.celery_tasks import app as celery_app
from osf import features
from website import settings as website_settings
from website.util import waterbutler
from website.files import utils as files_utils
from website.profile.utils import get_profile_image_url
from website.project.views.node import _view_project
from website.project.model import has_anonymous_link
from website.ember_osf_web.decorators import ember_flag_is_active
from website.project.decorators import (
    must_be_contributor_or_public,
    must_have_addon, must_not_be_registration,
    must_be_valid_project,
    must_have_permission,
    must_have_write_permission_or_public_wiki,
    must_not_be_retracted_registration,
)

from osf.exceptions import ValidationError, NodeStateError
from osf.utils.permissions import ADMIN, WRITE
from .exceptions import (
    NameEmptyError,
    NameInvalidError,
    NameMaximumLengthError,
    PageCannotRenameError,
    PageConflictError,
    PageNotFoundError,
    InvalidVersionError,
)

logger = logging.getLogger(__name__)

can_start_import = True

WIKI_NAME_EMPTY_ERROR = HTTPError(http_status.HTTP_400_BAD_REQUEST, data=dict(
    message_short='Invalid request',
    message_long='The wiki page name cannot be empty.'
))
WIKI_NAME_MAXIMUM_LENGTH_ERROR = HTTPError(http_status.HTTP_400_BAD_REQUEST, data=dict(
    message_short='Invalid request',
    message_long='The wiki page name cannot be more than 100 characters.'
))
WIKI_PAGE_CANNOT_RENAME_ERROR = HTTPError(http_status.HTTP_400_BAD_REQUEST, data=dict(
    message_short='Invalid request',
    message_long='The wiki page cannot be renamed.'
))
WIKI_PAGE_CONFLICT_ERROR = HTTPError(http_status.HTTP_409_CONFLICT, data=dict(
    message_short='Page conflict',
    message_long='A wiki page with that name already exists.'
))
WIKI_PAGE_NOT_FOUND_ERROR = HTTPError(http_status.HTTP_404_NOT_FOUND, data=dict(
    message_short='Not found',
    message_long='A wiki page could not be found.'
))
WIKI_INVALID_VERSION_ERROR = HTTPError(http_status.HTTP_400_BAD_REQUEST, data=dict(
    message_short='Invalid request',
    message_long='The requested version of this wiki page does not exist.'
))

WIKI_IMPORT_TASK_ALREADY_EXISTS = HTTPError(http_status.HTTP_400_BAD_REQUEST, data=dict(
    message_short='Running Task exists',
    message_long='\t' + 'Only 1 wiki import task can be executed on 1 node' + '\t'
))

WIKI_IMAGE_FOLDER = 'Wiki images'
WIKI_IMPORT_FOLDER = 'Imported Wiki workspace (temporary)'

def _get_wiki_versions(node, name, anonymous=False):
    # Skip if wiki_page doesn't exist; happens on new projects before
    # default "home" page is created
    wiki_page = WikiPage.objects.get_for_node(node, name)
    if wiki_page:
        versions = wiki_page.get_versions()
    else:
        return []

    return [
        {
            'version': version.identifier,
            'user_fullname': privacy_info_handle(version.user.fullname, anonymous, name=True),
            'date': '{} UTC'.format(version.created.replace(microsecond=0).isoformat().replace('T', ' ')),
        }
        for version in versions
    ]

def _get_wiki_pages_latest(node):
    return [
        {
            'name': page.wiki_page.page_name,
            'url': node.web_url_for('project_wiki_view', wname=page.wiki_page.page_name, _guid=True),
            'wiki_id': page.wiki_page._primary_key,
            'id': page.wiki_page.id,
            'wiki_content': _wiki_page_content(page.wiki_page.page_name, node=node),
            'sort_order': page.wiki_page.sort_order
        }
        for page in WikiPage.objects.get_wiki_pages_latest(node).order_by(F('wiki_page__sort_order'), F('name'))
    ]

def _get_wiki_child_pages_latest(node, parent):
    return [
        {
            'name': page.wiki_page.page_name,
            'url': node.web_url_for('project_wiki_view', wname=page.wiki_page.page_name, _guid=True),
            'wiki_id': page.wiki_page._primary_key,
            'id': page.wiki_page.id,
            'wiki_content': _wiki_page_content(page.wiki_page.page_name, node=node),
            'sort_order': page.wiki_page.sort_order
        }
        for page in WikiPage.objects.get_wiki_child_pages_latest(node, parent).order_by(F('wiki_page__sort_order'), F('name'))
    ]

def _get_wiki_api_urls(node, name, additional_urls=None):
    urls = {
        'base': node.api_url_for('project_wiki_home'),
        'delete': node.api_url_for('project_wiki_delete', wname=name),
        'rename': node.api_url_for('project_wiki_rename', wname=name),
        'content': node.api_url_for('wiki_page_content', wname=name),
        'settings': node.api_url_for('edit_wiki_settings'),
        'grid': node.api_url_for('project_wiki_grid_data', wname=name),
        'sort': node.api_url_for('project_update_wiki_page_sort')
    }
    if additional_urls:
        urls.update(additional_urls)
    return urls


def _get_wiki_web_urls(node, key, version=1, additional_urls=None):
    urls = {
        'base': node.web_url_for('project_wiki_home', _guid=True),
        'edit': node.web_url_for('project_wiki_view', wname=key, _guid=True),
        'home': node.web_url_for('project_wiki_home', _guid=True),
        'page': node.web_url_for('project_wiki_view', wname=key, _guid=True),
    }
    if additional_urls:
        urls.update(additional_urls)
    return urls


@must_be_valid_project
@must_have_write_permission_or_public_wiki
@must_have_addon('wiki', 'node')
def wiki_page_draft(wname, **kwargs):
    node = kwargs['node'] or kwargs['project']
    wiki_version = WikiVersion.objects.get_for_node(node, wname)

    return {
        'wiki_content': wiki_version.content if wiki_version else None,
        'wiki_draft': (wiki_version.get_draft(node) if wiki_version
                       else wiki_utils.get_sharejs_content(node, wname)),
    }

def _wiki_page_content(wname, wver=None, **kwargs):
    node = kwargs['node'] or kwargs['project']
    wiki_version = WikiVersion.objects.get_for_node(node, wname, wver)
    return {
        'wiki_content': wiki_version.content if wiki_version else '',
        'rendered_before_update': wiki_version.rendered_before_update if wiki_version else False
    }

@must_be_valid_project
@must_be_contributor_or_public
@must_have_addon('wiki', 'node')
def wiki_page_content(wname, wver=None, **kwargs):
    return _wiki_page_content(wname, wver=wver, **kwargs)

@must_be_valid_project  # injects project
@must_have_permission(WRITE)  # injects user, project
@must_not_be_registration
@must_have_addon('wiki', 'node')
def project_wiki_delete(auth, wname, **kwargs):
    node = kwargs['node'] or kwargs['project']
    wiki_name = wname.strip()
    wiki_page = WikiPage.objects.get_for_node(node, wiki_name)
    sharejs_uuid = wiki_utils.get_sharejs_uuid(node, wiki_name)

    if not wiki_page:
        raise HTTPError(http_status.HTTP_404_NOT_FOUND)

    child_wiki_pages = WikiPage.objects.get_for_node(node=node, parent=wiki_page.id)
    wiki_page.delete(auth)

    if child_wiki_pages:
        for page in child_wiki_pages:
            _child_wiki_delete(auth, node, page)

    wiki_utils.broadcast_to_sharejs('delete', sharejs_uuid, node)
    return {}

def _child_wiki_delete(auth, node, wiki_page):
    wiki_page.delete(auth)
    child_wiki_pages = WikiPage.objects.get_for_node(node=node, parent=wiki_page.id)
    for page in child_wiki_pages:
        _child_wiki_delete(auth, node, page)

@must_be_valid_project  # returns project
@must_be_contributor_or_public
@must_have_addon('wiki', 'node')
@must_not_be_retracted_registration
def project_wiki_view(auth, wname, path=None, **kwargs):
    node = kwargs['node'] or kwargs['project']
    anonymous = has_anonymous_link(node, auth)
    wiki_name = (wname or '').strip()
    wiki_key = to_mongo_key(wiki_name)
    wiki_page = WikiPage.objects.get_for_node(node, wiki_name)
    wiki_version = WikiVersion.objects.get_for_node(node, wiki_name)
    wiki_settings = node.get_addon('wiki')
    parent_wiki_page = WikiPage.objects.get(id=wiki_page.parent) if wiki_page and wiki_page.parent else None
    can_edit = (
        auth.logged_in and not
        node.is_registration and (
            node.has_permission(auth.user, WRITE) or
            wiki_settings.is_publicly_editable
        )
    )
    can_wiki_import = node.has_permission(auth.user, ADMIN)
    versions = _get_wiki_versions(node, wiki_name, anonymous=anonymous)

    # Determine panels used in view
    panels = {'view', 'edit', 'compare', 'menu'}
    if request.args and set(request.args).intersection(panels):
        panels_used = [panel for panel in request.args if panel in panels]
        num_columns = len(set(panels_used).intersection({'view', 'edit', 'compare'}))
        if num_columns == 0:
            panels_used.append('view')
            num_columns = 1
    else:
        panels_used = ['view', 'menu']
        num_columns = 1

    try:
        view = wiki_utils.format_wiki_version(
            version=request.args.get('view'),
            num_versions=len(versions),
            allow_preview=True,
        )
        compare = wiki_utils.format_wiki_version(
            version=request.args.get('compare'),
            num_versions=len(versions),
            allow_preview=False,
        )
    except InvalidVersionError:
        raise WIKI_INVALID_VERSION_ERROR

    # ensure home is always lower case since it cannot be renamed
    if wiki_name.lower() == 'home':
        wiki_name = 'home'

    if wiki_version:
        version = wiki_version.identifier
        is_current = wiki_version.is_current
        content = wiki_version.html(node)
        rendered_before_update = wiki_version.rendered_before_update
        markdown = wiki_version.content
    else:
        version = 'NA'
        is_current = False
        content = ''
        rendered_before_update = False
        markdown = ''

    if can_edit:
        if wiki_key not in node.wiki_private_uuids:
            wiki_utils.generate_private_uuid(node, wiki_name)
        sharejs_uuid = wiki_utils.get_sharejs_uuid(node, wiki_name)
    else:
        if not wiki_page and wiki_key != 'home':
            raise WIKI_PAGE_NOT_FOUND_ERROR
        if 'edit' in request.args:
            if wiki_settings.is_publicly_editable:
                raise HTTPError(http_status.HTTP_401_UNAUTHORIZED)
            if node.can_view(auth):
                return redirect(node.web_url_for('project_wiki_view', wname=wname, _guid=True))
            raise HTTPError(http_status.HTTP_403_FORBIDDEN)
        sharejs_uuid = None

    # Opens 'edit' panel when home wiki is empty
    if not content and can_edit and wiki_name == 'home':
        panels_used.append('edit')

    # Default versions for view and compare
    version_settings = {
        'view': view or ('preview' if 'edit' in panels_used else 'current'),
        'compare': compare or 'previous',
    }

    # Get import folder
    root_dir = BaseFileNode.objects.filter(target_object_id=node.id, is_root=True).values('id').first()
    parent_dirs = BaseFileNode.objects.filter(target_object_id=node.id, type='osf.osfstoragefolder', parent=root_dir['id'], deleted__isnull=True)
    import_dirs = []
    for parent_dir in parent_dirs:
        wiki_dir = BaseFileNode.objects.filter(target_object_id=node.id, type='osf.osfstoragefolder', parent=parent_dir.id, deleted__isnull=True).first()
        if not wiki_dir:
            continue
        wiki_file_name = wiki_dir.name + '.md'
        if BaseFileNode.objects.filter(target_object_id=node.id, type='osf.osfstoragefile', parent=wiki_dir.id, name=wiki_file_name, deleted__isnull=True).exists():
            dict = {
                'id': parent_dir._id,
                'name': parent_dir.name
            }
            import_dirs.append(dict)

    alive_task_id = WikiImportTask.objects.values_list('task_id').filter(status=WikiImportTask.STATUS_RUNNING, node=node)

    pages_current = _get_wiki_pages_latest(node)
    sortable_pages = [item for item in pages_current if item['name'] != 'home']

    ret = {
        'wiki_id': wiki_page._primary_key if wiki_page else None,
        'wiki_name': wiki_page.page_name if wiki_page else wiki_name,
        'wiki_content': content,
        'wiki_markdown': markdown,
        'parent_wiki_name': parent_wiki_page.page_name if parent_wiki_page else '',
        'import_dirs': import_dirs,
        'alive_task_id': alive_task_id,
        'rendered_before_update': rendered_before_update,
        'page': wiki_page,
        'version': version,
        'versions': versions,
        'sharejs_uuid': sharejs_uuid or '',
        'sharejs_url': settings.SHAREJS_URL,
        'y_websocket_url': settings.Y_WEBSOCKET_URL,
        'is_current': is_current,
        'version_settings': version_settings,
        'pages_current': _get_wiki_pages_latest(node),
        'sortable_pages': sortable_pages,
        'category': node.category,
        'panels_used': panels_used,
        'num_columns': num_columns,
        'urls': {
            'api': _get_wiki_api_urls(node, wiki_name, {
                'content': node.api_url_for('wiki_page_content', wname=wiki_name),
                'draft': node.api_url_for('wiki_page_draft', wname=wiki_name),
            }),
            'web': _get_wiki_web_urls(node, wiki_name),
            'profile_image': get_profile_image_url(auth.user, 25),
        },
    }
    ret.update(_view_project(node, auth, primary=True))
    ret['user']['can_edit_wiki_body'] = can_edit
    ret['user']['can_wiki_import'] = can_wiki_import
    return ret


@must_be_valid_project  # injects node or project
@must_have_write_permission_or_public_wiki  # injects user
@must_not_be_registration
@must_have_addon('wiki', 'node')
def project_wiki_edit_post(auth, wname, **kwargs):
    node = kwargs['node'] or kwargs['project']
    # normalize NFC
    wiki_name = unicodedata.normalize('NFC', wname)
    wiki_name = wiki_name.strip()
    wiki_version = WikiVersion.objects.get_for_node(node, wiki_name)
    redirect_url = node.web_url_for('project_wiki_view', wname=wiki_name, _guid=True)
#    form_wiki_content = request.form['content']

    # ensure home is always lower case since it cannot be renamed
    if wiki_name.lower() == 'home':
        wiki_name = 'home'

    get_json = request.get_json()
    form_wiki_content = get_json['markdown']

    # normalize NFC
    form_wiki_content = unicodedata.normalize('NFC', form_wiki_content)

    if wiki_version:
        # Only update wiki if content has changed
        if form_wiki_content != wiki_version.content:
            wiki_version.wiki_page.update(auth.user, form_wiki_content)
            ret = {'status': 'success'}
        else:
            ret = {'status': 'unmodified'}
    else:
        # Create a wiki
        WikiPage.objects.create_for_node(node, wiki_name, form_wiki_content, auth)
        ret = {'status': 'success'}
    return ret, http_status.HTTP_302_FOUND, None, redirect_url

@must_be_valid_project  # injects node or project
@must_have_permission(ADMIN)
@must_not_be_registration
@must_have_addon('wiki', 'node')
def edit_wiki_settings(node, auth, **kwargs):
    wiki_settings = node.get_addon('wiki')
    permissions = request.get_json().get('permission', None)

    if not wiki_settings:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data=dict(
            message_short='Invalid request',
            message_long='Cannot change wiki settings without a wiki'
        ))

    if permissions == 'public':
        permissions = True
    elif permissions == 'private':
        permissions = False
    else:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data=dict(
            message_short='Invalid request',
            message_long='Permissions flag used is incorrect.'
        ))

    try:
        wiki_settings.set_editing(permissions, auth, log=True)
    except NodeStateError as e:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data=dict(
            message_short="Can't change privacy",
            message_long=str(e)
        ))

    return {
        'status': 'success',
        'permissions': permissions,
    }

@must_be_logged_in
@must_be_valid_project
def get_node_wiki_permissions(node, auth, **kwargs):
    return wiki_utils.serialize_wiki_settings(auth.user, [node])

@must_be_valid_project
@must_have_addon('wiki', 'node')
@ember_flag_is_active(features.EMBER_PROJECT_WIKI)
def project_wiki_home(**kwargs):
    node = kwargs['node'] or kwargs['project']
    return redirect(node.web_url_for('project_wiki_view', wname='home', _guid=True))


@must_be_valid_project  # injects project
@must_be_contributor_or_public
@must_have_addon('wiki', 'node')
def project_wiki_id_page(auth, wid, **kwargs):
    node = kwargs['node'] or kwargs['project']
    wiki = WikiPage.objects.get_for_node(node, id=wid)
    if wiki:
        return redirect(node.web_url_for('project_wiki_view', wname=wiki.page_name, _guid=True))
    else:
        raise WIKI_PAGE_NOT_FOUND_ERROR


@must_be_valid_project
@must_have_write_permission_or_public_wiki
@must_not_be_registration
@must_have_addon('wiki', 'node')
def project_wiki_edit(wname, **kwargs):
    node = kwargs['node'] or kwargs['project']
    return redirect(node.web_url_for('project_wiki_view', wname=wname, _guid=True) + '?edit&view&menu')


@must_be_valid_project
@must_be_contributor_or_public
@must_have_addon('wiki', 'node')
def project_wiki_compare(wname, wver, **kwargs):
    node = kwargs['node'] or kwargs['project']
    return redirect(node.web_url_for('project_wiki_view', wname=wname, _guid=True) + '?view&compare={0}&menu'.format(wver))


@must_not_be_registration
@must_have_permission(WRITE)
@must_have_addon('wiki', 'node')
def project_wiki_rename(auth, wname, **kwargs):
    """View that handles user the X-editable input for wiki page renaming.

    :param wname: The target wiki page name.
    :param-json value: The new wiki page name.
    """
    node = kwargs['node'] or kwargs['project']
    wiki_name = wname.strip()
    new_wiki_name = request.get_json().get('value', None)
    wiki_page = WikiPage.objects.get_for_node(node, wiki_name)

    if not wiki_page:
        raise WIKI_PAGE_NOT_FOUND_ERROR

    try:
        wiki_page.rename(new_wiki_name, auth)
    except NameEmptyError:
        raise WIKI_NAME_EMPTY_ERROR
    except NameInvalidError as error:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data=dict(
            message_short='Invalid name',
            message_long=error.args[0]
        ))
    except NameMaximumLengthError:
        raise WIKI_NAME_MAXIMUM_LENGTH_ERROR
    except PageCannotRenameError:
        raise WIKI_PAGE_CANNOT_RENAME_ERROR
    except PageConflictError:
        raise WIKI_PAGE_CONFLICT_ERROR
    except PageNotFoundError:
        raise WIKI_PAGE_NOT_FOUND_ERROR
    except ValidationError as err:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data=dict(
            message_short='Invalid request',
            message_long=err.messages[0]
        ))
    else:
        sharejs_uuid = wiki_utils.get_sharejs_uuid(node, new_wiki_name)
        wiki_utils.broadcast_to_sharejs('redirect', sharejs_uuid, node, new_wiki_name)


@must_be_valid_project  # returns project
@must_have_permission(ADMIN)  # returns user, project
@must_not_be_registration
@must_have_addon('wiki', 'node')
def project_wiki_validate_name(wname, auth, node, p_wname=None, **kwargs):
    # normalize NFC
    wiki_name = unicodedata.normalize('NFC', wname)
    wiki_name = wiki_name.strip()
    wiki = WikiPage.objects.get_for_node(node, wiki_name)

    if wiki or wiki_name.lower() == 'home':
        raise HTTPError(http_status.HTTP_409_CONFLICT, data=dict(
            message_short='Wiki page name conflict.',
            message_long='A wiki page with that name already exists.'
        ))

    parent_wiki_id = None
    if p_wname:
        p_wname = unicodedata.normalize('NFC', p_wname)
        parent_wiki_name = p_wname.strip()
        parent_wiki = WikiPage.objects.get_for_node(node, parent_wiki_name)
        if not parent_wiki:
            if parent_wiki_name.lower() == 'home':
                # Create a wiki
                parent_wiki = WikiPage.objects.create_for_node(node, parent_wiki_name, '', auth)
            else:
                raise HTTPError(http_status.HTTP_404_NOT_FOUND, data=dict(
                    message_short='Parent Wiki page nothing.',
                    message_long='The parent wiki page does not exist.'
                ))
        parent_wiki_id = parent_wiki.id

    WikiPage.objects.create_for_node(node, wiki_name, '', auth, parent_wiki_id)
    return {'message': wiki_name}

@must_be_valid_project
@must_be_contributor_or_public
def project_wiki_grid_data(auth, node, **kwargs):
    pages = []
    project_wiki_pages = {
        'title': 'Project Wiki Pages',
        'kind': 'folder',
        'type': 'heading',
        'children': format_project_wiki_pages(node, auth)
    }
    pages.append(project_wiki_pages)

    component_wiki_pages = {
        'title': 'Component Wiki Pages',
        'kind': 'folder',
        'type': 'heading',
        'children': format_component_wiki_pages(node, auth)
    }
    if len(component_wiki_pages['children']) > 0:
        pages.append(component_wiki_pages)

    return pages


def format_home_wiki_page(node):
    home_wiki = WikiPage.objects.get_for_node(node, 'home')
    home_wiki_page = {
        'page': {
            'url': node.web_url_for('project_wiki_home'),
            'name': 'Home',
            'id': 'None',
        }
    }
    if home_wiki:
        home_wiki_page = {
            'page': {
                'url': node.web_url_for('project_wiki_view', wname='home', _guid=True),
                'name': 'Home',
                'id': home_wiki._primary_key,
            }
        }
        child_wiki_pages = _format_child_wiki_pages(node, home_wiki.id)
        if child_wiki_pages:
            home_wiki_page['children'] = child_wiki_pages
            home_wiki_page['kind'] = 'folder'
    return home_wiki_page


def format_project_wiki_pages(node, auth):
    pages = []
    can_edit = node.has_permission(auth.user, WRITE) and not node.is_registration
    project_wiki_pages = _get_wiki_pages_latest(node)
    home_wiki_page = format_home_wiki_page(node)
    pages.append(home_wiki_page)
    for wiki_page in project_wiki_pages:
        if wiki_page['name'] != 'home':
            has_content = bool(wiki_page['wiki_content'].get('wiki_content'))
            page = {
                'page': {
                    'url': wiki_page['url'],
                    'name': wiki_page['name'],
                    'id': wiki_page['wiki_id'],
                    'sort_order': wiki_page['sort_order']
                }
            }
            child_wiki_pages = _format_child_wiki_pages(node, wiki_page['id'])
            page['children'] = child_wiki_pages
            if child_wiki_pages:
                page['kind'] = 'folder'

            if can_edit or has_content:
                pages.append(page)
    return pages


def _format_child_wiki_pages(node, parent):
    pages = []
    child_wiki_pages = _get_wiki_child_pages_latest(node, parent)
    if not child_wiki_pages:
        return pages

    for wiki_page in child_wiki_pages:
        if wiki_page['name'] != 'home':
            page = {
                'page': {
                    'url': wiki_page['url'],
                    'name': wiki_page['name'],
                    'id': wiki_page['wiki_id'],
                    'sort_order': wiki_page['sort_order']
                }
            }
            grandchild_wiki_pages = _format_child_wiki_pages(node, wiki_page['id'])
            page['children'] = grandchild_wiki_pages
            if grandchild_wiki_pages:
                page['kind'] = 'folder'

            pages.append(page)
    return pages


def format_component_wiki_pages(node, auth):
    pages = []
    for node in node.get_nodes(is_deleted=False):
        if any([not node.can_view(auth),
                not node.has_addon('wiki')]):
            continue
        else:
            serialized = serialize_component_wiki(node, auth)
            if serialized:
                pages.append(serialized)
    return pages


def serialize_component_wiki(node, auth):
    children = []
    url = node.web_url_for('project_wiki_view', wname='home', _guid=True)
    home_has_content = bool(_wiki_page_content('home', node=node).get('wiki_content'))
    component_home_wiki = {
        'page': {
            'url': url,
            'name': 'Home',
            # Handle pointers
            'id': node._id
        }
    }
    home_wiki = WikiPage.objects.get_for_node(node, 'home')
    if home_wiki:
        child_wiki_pages = _format_child_wiki_pages(node, home_wiki.id)
        if child_wiki_pages:
            component_home_wiki['children'] = child_wiki_pages
            component_home_wiki['kind'] = 'folder'

    can_edit = node.has_permission(auth.user, WRITE) and not node.is_registration
    if can_edit or home_has_content:
        children.append(component_home_wiki)

    for page in _get_wiki_pages_latest(node):
        if page['name'] != 'home':
            has_content = bool(page['wiki_content'].get('wiki_content'))
            component_page = {
                'page': {
                    'url': page['url'],
                    'name': page['name'],
                    'id': page['wiki_id'],
                    'sort_order': page['sort_order']
                }
            }
            child_wiki_pages = _format_child_wiki_pages(node, page['id'])
            component_page['children'] = child_wiki_pages
            if child_wiki_pages:
                component_page['kind'] = 'folder'
            if can_edit or has_content:
                children.append(component_page)

    if len(children) > 0:
        component = {
            'page': {
                'name': node.title,
                'url': url,
            },
            'kind': 'component',
            'category': node.category,
            'pointer': not node.primary,
            'children': children,
        }
        return component
    return None

@must_be_valid_project
def project_wiki_validate_import(dir_id, node, **kwargs):
    wiki_utils.check_dir_id(dir_id, node)
    node_id = wiki_utils.get_node_guid(node)
    task = tasks.run_project_wiki_validate_import.delay(dir_id, node_id)
    task_id = task.id
    return { 'taskId': task_id }

def project_wiki_validate_import_process(dir_id, node):
    global can_start_import
    can_start_import = True
    import_dir = BaseFileNode.objects.values('id', 'name').get(_id=dir_id)
    import_objects = BaseFileNode.objects.filter(target_object_id=node.id, parent=import_dir['id'], deleted__isnull=True)
    info_list = []
    duplicated_folder_list = []
    for obj in import_objects:
        if obj.type == 'osf.osf.osfstoragefile':
            logger.warn(f'This file cannot be imported: {obj.name}')
            info = {
                'path': import_dir['name'],
                'name': obj.name,
                'status': 'invalid',
                'message': 'This file cannot be imported.',
                'parent_name': None,
            }
            info_list.extend(info)
            continue

        child_info_list = _validate_import_folder(node, obj, '')
        info_list.extend(child_info_list)
    duplicated_folder_list = _validate_import_duplicated_directry(info_list)
    return {
        'data': info_list,
        'duplicated_folder': duplicated_folder_list,
        'canStartImport': can_start_import,
    }

def _validate_import_folder(node, folder, parent_path):
    index = parent_path.rfind('/')
    parent_wiki_name = parent_path[index+1:] if index != -1 else None
    parent_wiki_fullpath = wiki_utils.get_wiki_fullpath(node, parent_wiki_name)
    p_numbering = None
    # check duplication of parent_wiki_name
    if parent_path != parent_wiki_fullpath:
        p_numbering = wiki_utils.get_wiki_numbering(node, parent_wiki_name)
    if isinstance(p_numbering, int):
        parent_wiki_name = parent_wiki_name + '(' + str(p_numbering) + ')'
        path = parent_path[:index+1] + parent_wiki_name + '/' + folder.name
    else:
        path = parent_path + '/' + folder.name
    info_list = []
    wiki_name = folder.name
    wiki_file_name = folder.name + '.md'
    if not BaseFileNode.objects.filter(target_object_id=node.id, type='osf.osfstoragefile', parent=folder.id, name=wiki_file_name, deleted__isnull=True).exists():
        logger.warn(f'The wiki page does not exist, so the subordinate pages are not processed: {folder.name}')
        info = {
            'path': path,
            'original_name': folder.name,
            'name': folder.name,
            'status': 'invalid',
            'message': 'The wiki page does not exist, so the subordinate pages are not processed.',
        }
        info_list.append(info)
        return info_list

    child_objects = BaseFileNode.objects.filter(target_object_id=node.id, parent=folder.id, deleted__isnull=True)
    for obj in child_objects:
        if obj.type == 'osf.osfstoragefolder':
            child_info_list = _validate_import_folder(node, obj, path)
            info_list.extend(child_info_list)
        else:
            if obj.name == wiki_file_name:
                logger.warn(f'valid wiki page: {obj.name}')
                info = {
                    'parent_wiki_name': parent_wiki_name,
                    'path': path,
                    'original_name': wiki_name,
                    'wiki_name': wiki_name,
                    'status': 'valid',
                    'message': '',
                    '_id': obj._id
                }
                info = _validate_import_wiki_exists_duplicated(node, info)
                info_list.append(info)
                continue

    return info_list

def _validate_import_wiki_exists_duplicated(node, info):
    w_name = info['wiki_name']
    p_wname = info['parent_wiki_name']

    global can_start_import
    # get wiki full path
    fullpath = wiki_utils.get_wiki_fullpath(node, w_name)
    wiki = WikiPage.objects.get_for_node(node, w_name)
    if wiki:
        if fullpath == info['path']:
            # if the wiki exists, update info list
            info['status'] = 'valid_exists'
            info['numbering'] = wiki_utils.get_wiki_numbering(node, w_name)
            can_start_import = False
        else:
            # if the wiki duplicated, update info list
            info['status'] = 'valid_duplicated'
            info['numbering'] = wiki_utils.get_wiki_numbering(node, w_name)
            info['wiki_name'] = info['wiki_name'] + '(' + str(info['numbering']) + ')'
            info['path'] = info['path'] + '(' + str(info['numbering']) + ')'
            can_start_import = False
    return info

def _validate_import_duplicated_directry(info_list):
    folder_name_list = []
    # create original folder name list
    for info in info_list:
        folder_name_list.append(info['original_name'])
    # extract duplicate page names
    duplicated_folder_list = [k for k, v in collections.Counter(folder_name_list).items() if v > 1]
    return duplicated_folder_list

@must_be_valid_project  # returns project
@must_have_permission(ADMIN)  # returns user, project
@must_not_be_registration
@must_have_addon('wiki', 'node')
def project_wiki_import(dir_id, auth, node, **kwargs):
    wiki_utils.check_dir_id(dir_id, node)
    node_id = wiki_utils.get_node_guid(node)
    current_user_id = get_current_user_id()
    data = request.get_json()
    data_json = json.dumps(data)
    task = tasks.run_project_wiki_import.delay(data_json, dir_id, current_user_id, node_id)
    task_id = task.id
    return { 'taskId': task_id }

def project_wiki_import_process(data, dir_id, task_id, auth, node):
    logger.info('----WIKI IMPORT DIRECTORY_ID: {}, PROJECT_NAME: {} ----'.format(dir_id, node.title))
    WikiImportTask.objects.create(node=node, task_id=task_id, status=WikiImportTask.STATUS_RUNNING, creator=auth.user)
    check_running_task(task_id, node)
    ret = []
    wiki_id_list = []
    res_child = []
    import_errors = []
    user = auth.user
    pid = wiki_utils.get_node_guid(node)
    osf_cookie = user.get_or_create_cookie().decode()
    creator, creator_auth = get_creator_auth_header(user)
    task = AbortableAsyncResult(task_id, app=celery_app)
    # GET markdown content from wb
    wiki_info = _get_md_content_from_wb(data, node, creator_auth, task)
    if wiki_info is None:
        set_wiki_import_task_proces_end(node)
        logger.info('wiki import process is stopped')
        return { 'aborted': True }
    logger.info('got markdown content from wb')
    # Get or create 'Wiki images'
    root_id = BaseFileNode.objects.get(target_object_id=node.id, is_root=True).id
    wiki_images_folder_id, wiki_images_folder_path = _get_or_create_wiki_folder(osf_cookie, node, root_id, user, creator_auth, WIKI_IMAGE_FOLDER)
    logger.info('got or created Wiki images folder')
     # Get or create 'Imported Wiki workspace (temporary)'
    wiki_import_folder_id, wiki_import_folder_path = _get_or_create_wiki_folder(osf_cookie, node, wiki_images_folder_id, user, creator_auth, WIKI_IMPORT_FOLDER, wiki_images_folder_path)
    logger.info('got or created Imported Wiki workspace (temporary) folder')
    random_name = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    # Create folder sorting copy import directory
    wiki_import_sorting_folder_id, wiki_import_sorting_folder_path = _create_wiki_folder(osf_cookie, pid, random_name, wiki_import_folder_path)
    logger.info('created sorting copy import folder')
    copy_to_id = wiki_import_sorting_folder_path.split('/')[1]
    # Copy Import Directory
    cloned_id = _wiki_copy_import_directory(copy_to_id, dir_id, node)
    logger.info('copied import directory')
    # Replace Wiki Content
    replaced_wiki_info = _wiki_content_replace(wiki_info, cloned_id, node, task)
    logger.info('replaced wiki content')
    if replaced_wiki_info is None:
        set_wiki_import_task_proces_end(node)
        logger.info('wiki import process is stopped')
        return { 'aborted': True }
    # Import top hierarchy wiki page
    for info in replaced_wiki_info:
        if info['parent_wiki_name'] is None:
            try:
                res_root, wiki_id = _wiki_import_create_or_update(info['path'], info['wiki_content'], auth, node, task)
                ret.append(res_root)
                wiki_id_list.append(wiki_id)
            except ImportTaskAborted:
                tasks.run_update_search_and_bulk_index.delay(pid, wiki_id_list)
                set_wiki_import_task_proces_end(node)
                logger.info('wiki import process is stopped')
                return { 'aborted': True }
            except Exception as err:
                logger.error(err)
    logger.info('imported top hierarchy wiki pages')
    max_depth = wiki_utils.get_max_depth(replaced_wiki_info)
    # Import child wiki pages
    for depth in range(1, max_depth+1):
        try:
            res_child, child_wiki_id_list = _import_same_level_wiki(replaced_wiki_info, depth, auth, node, task)
            ret.extend(res_child)
            wiki_id_list.extend(child_wiki_id_list)
        except ImportTaskAborted:
            tasks.run_update_search_and_bulk_index.delay(pid, wiki_id_list)
            set_wiki_import_task_proces_end(node)
            logger.info('wiki import process is stopped')
            return { 'aborted': True }
        except Exception as err:
            logger.error(err)
    logger.info('imported child hierarchy wiki pages')
    # Create import error page list
    import_errors = wiki_utils.create_import_error_list(data, ret)
    logger.info('created import error page list')
    # Run task to update elasticsearch index
    tasks.run_update_search_and_bulk_index.delay(pid, wiki_id_list)
    logger.info('ran task to update elasticsearch index')
    # Change task status to complete
    change_task_status(task_id, WikiImportTask.STATUS_COMPLETED, True)
    logger.info('complete wiki import')
    return {'ret': ret, 'import_errors': import_errors}

def _replace_wiki_link_notation(node, link_matches, wiki_content, info, all_children_name, all_children_obj, dir_id):
    wiki_name = info['original_name']
    match_path = ''
    for match in link_matches:
        match_path, tooltip_match = _exclude_tooltip(match['path'])
        has_slash, has_sharp, has_dot, is_url = _exclude_symbols(match_path)
        if bool(is_url):
            continue
        if has_slash:
            continue
        if has_sharp:
            if has_dot:
                # relace file name
                wiki_content = _replace_file_name(node, wiki_name, wiki_content, match, 'link', dir_id, match_path, tooltip_match, all_children_name, all_children_obj)
                continue
            continue

        # check whether wiki or not
        is_wiki = _check_wiki_name_exist(node, match_path, all_children_name)
        if is_wiki:
            if tooltip_match:
                wiki_content = wiki_content.replace('[' + match['title'] + '](' + match['path'] + ')', '[' + match['title'] + '](../' + tooltip_match['path'] + '/ "' + tooltip_match['tooltip'] + '")')
            else:
                wiki_content = wiki_content.replace('[' + match['title'] + '](' + match['path'] + ')', '[' + match['title'] + '](../' + match['path'] + '/)')
        else:
            # If not wiki, check whether attachment file or not
            wiki_content = _replace_file_name(node, wiki_name, wiki_content, match, 'link', dir_id, match_path, tooltip_match, all_children_name, all_children_obj)
    return wiki_content

def _check_wiki_name_exist(node, checked_name, all_children_name):
    replaced_wiki_name = _replace_common_rule(checked_name)
    # normalize NFC
    replaced_wiki_name = unicodedata.normalize('NFC', replaced_wiki_name)
    wiki = WikiPage.objects.get_for_node(node, replaced_wiki_name)
    if wiki:
        return True
    else:
        # check import directory(copyed)
        return replaced_wiki_name in all_children_name

def _replace_file_name(node, wiki_name, wiki_content, match, notation, dir_id, match_path, tooltip_match, all_children_name, all_children_obj):
    # check whether attachment file or not
    file_id = _check_attachment_file_name_exist(wiki_name, match_path, dir_id, all_children_name, all_children_obj)
    if file_id:
        # replace process of file name
        node_guid = wiki_utils.get_node_guid(node)
        if notation == 'image':
            url = website_settings.WATERBUTLER_URL + '/v1/resources/' +  node_guid + '/providers/osfstorage/' + file_id + '?mode=render'
            #wurl = waterbutler_api_url_for(node_guid, 'osfstorage', path='/{}?mode=render'.format(file_id), _internal=True)
            if tooltip_match:
                wiki_content = wiki_content.replace('![' + match['title'] + '](' + match['path'] + ')', '![' + match['title'] + '](' + url + ' "' + tooltip_match['tooltip'] + '")')
            else:
                wiki_content = wiki_content.replace('![' + match['title'] + '](' + match['path'] + ')', '![' + match['title'] + '](' + url + ')')
        elif notation == 'link':
            file_obj = BaseFileNode.objects.get(_id=file_id)
            url = website_settings.DOMAIN + node_guid + '/files/osfstorage/' + file_id
            if tooltip_match:
                wiki_content = wiki_content.replace('[' + match['title'] + '](' + match['path'] + ')', '[' + match['title'] + '](' + url + ' "' + tooltip_match['tooltip'] + '")')
            else:
                wiki_content = wiki_content.replace('[' + match['title'] + '](' + match['path'] + ')', '[' + match['title'] + '](' + url + ')')
    return wiki_content

def _exclude_symbols(path):
    has_slash = '/' in path
    has_sharp = '#' in path
    has_dot = '.' in path
    rep_url = r"^https?://[\w/:%#\$&\?\(\)~\.=\+\-]+$"
    is_url = re.match(rep_url, path)
    return has_slash, has_sharp, has_dot, is_url

def _exclude_tooltip(match_path):
    rep_tooltip_single = r'(?P<path>.+?)[ ]+\'(?P<tooltip>.+?(?<!\\)(?:\\\\)*)\''
    rep_tooltip_double = r'(?P<path>.+?)[ ]+"(?P<tooltip>.+?(?<!\\)(?:\\\\)*)"'
    match_tooltip_single = list(re.finditer(rep_tooltip_single, match_path))
    match_tooltip_double = list(re.finditer(rep_tooltip_double, match_path))
    # exclude tooltip
    if match_tooltip_single or match_tooltip_double:
        if match_tooltip_single:
            exclude_tooltop_match = match_tooltip_single[0]
            exclude_tooltip_path = exclude_tooltop_match['path']
        elif match_tooltip_double:
            exclude_tooltop_match = match_tooltip_double[0]
            exclude_tooltip_path = exclude_tooltop_match['path']
        return exclude_tooltip_path, exclude_tooltop_match
    else:
        return match_path, None

def _check_attachment_file_name_exist(wiki_name, file_name, dir_id, all_children_name, all_children_obj):
    # check file name contains slash
    has_hat = '^' in file_name
    if has_hat:
        another_wiki_name = file_name.split('^')[0]
        file_name = file_name.split('^')[1]
        # check as wikiName/fileName
        file_id = _process_attachment_file_name_exist(has_hat, another_wiki_name, file_name, dir_id, all_children_name, all_children_obj)
    else:
        # check as fileName
        file_id = _process_attachment_file_name_exist(has_hat, wiki_name, file_name, dir_id, all_children_name, all_children_obj)

    return file_id

def _process_attachment_file_name_exist(has_hat, wiki_name, file_name, dir_id, all_children_name, all_children_obj):
    # check as fileName
    replaced_wiki_name = _replace_common_rule(wiki_name) if has_hat else wiki_name
    replaced_file_name = _replace_common_rule(file_name)
    try:
        idx = all_children_name.index(replaced_wiki_name)
        parent_directory = all_children_obj[idx]
        # normalize NFC
        replaced_file_name = unicodedata.normalize('NFC', replaced_file_name)
        child_file = parent_directory._children.get(name=replaced_file_name, type='osf.osfstoragefile', deleted__isnull=True)
        return child_file._id
    except Exception as err:
        pass

    return None

def _replace_wiki_image(node, image_matches, wiki_content, wiki_info, dir_id, all_children_name, all_children_obj):
    wiki_name = wiki_info['original_name']
    for match in image_matches:
        match_path, tooltip_match = _exclude_tooltip(match['path'])
        has_slash = '/' in match_path
        if has_slash:
            continue
        wiki_content = _replace_file_name(node, wiki_name, wiki_content, match, 'image', dir_id, match_path, tooltip_match, all_children_name, all_children_obj)
    return wiki_content

# for Search wikiName or fileName
def _replace_common_rule(name):
    has_plus = '+' in name
    # decode
    if has_plus:
        decoded_name = urllib.parse.unquote_plus(name)
    else:
        decoded_name = urllib.parse.unquote(name)
    return decoded_name

def _get_or_create_wiki_folder(osf_cookie, node, parent_id, user, creator_auth, folder_name, parent_path='osfstorage/'):
    folder_id = ''
    folder_path = ''
    p_guid = wiki_utils.get_node_guid(node)
    try:
        folder = BaseFileNode.objects.get(target_object_id=node.id, parent_id=parent_id, type='osf.osfstoragefolder', name=folder_name, deleted__isnull=True)
    except ObjectDoesNotExist:
        return _create_wiki_folder(osf_cookie, p_guid, folder_name, parent_path)
    folder_id = folder.id
    folder_path = 'osfstorage/{}/'.format(folder._id)
    return folder_id, folder_path

def _create_wiki_folder(osf_cookie, p_guid, folder_name, parent_path):
    try:
        folder_response = waterbutler.create_folder(osf_cookie, p_guid, folder_name, parent_path)
        folder_response.raise_for_status()
    except Exception as err:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data=dict(
            message_short='Error when create wiki folder',
            message_long= '\t' + 'An error occures when create wiki folder : ' + folder_name + '\t'
        ))
    folder_path = folder_response.json()['data']['id']
    _id = (folder_response.json()['data']['attributes']['path']).strip('/')
    folder_id = BaseFileNode.objects.get(_id=_id).id
    return folder_id, folder_path

def _get_md_content_from_wb(data, node, creator_auth, task):
    node_id = wiki_utils.get_node_guid(node)
    for i, info in enumerate(data):
        if task.is_aborted():
            return None
        try:
            response = requests.get(waterbutler_api_url_for(node_id, 'osfstorage', path='/' + info['_id'], _internal=True), headers=creator_auth)
            response.raise_for_status()
            data[i]['wiki_content'] = (response._content).decode()
        except Exception as err:
            logger.error(err)
            logger.error('Failed to get {} content from WB'.format(data[i]['wiki_name']))
    return data

def _wiki_copy_import_directory(copy_to_id, copy_from_id, node):
    copy_from = BaseFileNode.objects.get(_id=copy_from_id)
    copy_to = BaseFileNode.objects.get(_id=copy_to_id)
    cloned = files_utils.copy_files(copy_from, node, copy_to)
    cloned_id = cloned._id
    return cloned_id

def _wiki_content_replace(wiki_info, dir_id, node, task):
    replaced_wiki_info = []
    rep_link = r'(?<!\\|\!)\[(?P<title>.+?(?<!\\)(?:\\\\)*)\]\((?P<path>.+?)(?<!\\)\)'
    rep_image = r'(?<!\\)!\[(?P<title>.*?(?<!\\)(?:\\\\)*)\]\((?P<path>.+?)(?<!\\)\)'
    all_children_name, all_children_obj = wiki_utils.get_all_wiki_name_import_directory(dir_id)
    for info in wiki_info:
        if task.is_aborted():
            return None
        if not 'wiki_content' in info:
            continue
        gc.collect()
        wiki_content = info['wiki_content']
        link_matches = list(re.finditer(rep_link, wiki_content))
        image_matches = list(re.finditer(rep_image, wiki_content))
        info['wiki_content'] = _replace_wiki_image(node, image_matches, wiki_content, info, dir_id, all_children_name, all_children_obj)
        info['wiki_content'] = _replace_wiki_link_notation(node, link_matches, info['wiki_content'], info, all_children_name, all_children_obj, dir_id)
        replaced_wiki_info.append(info)
    return replaced_wiki_info

def _wiki_import_create_or_update(path, data, auth, node, task, p_wname=None, **kwargs):
    if task.is_aborted():
        raise ImportTaskAborted
    parent_wiki_id = None
    updated_wiki_id = None
    # normalize NFC
    data = unicodedata.normalize('NFC', data)
    wiki_name = os.path.splitext(os.path.basename(unicodedata.normalize('NFC', path)))[0]
    ret = {}
    if p_wname:
        p_wname = unicodedata.normalize('NFC', p_wname)
        parent_wiki_name = p_wname.strip()
        parent_wiki = WikiPage.objects.get_for_node(node, parent_wiki_name)
        if not parent_wiki:
            # Import Error
            return {}
        parent_wiki_id = parent_wiki.id
    wiki_version = WikiVersion.objects.get_for_node(node, wiki_name)
    # ensure home is always lower case since it cannot be renamed
    if wiki_name.lower() == 'home':
        wiki_name = 'home'
    if wiki_version:
        # Only update wiki if content has changed
        if data != wiki_version.content:
            wiki_version.wiki_page.update(auth.user, data, True)
            updated_wiki_id = wiki_version.wiki_page.id
            ret = {'status': 'success', 'path': path}
        else:
            ret = {'status': 'unmodified', 'path': path}
    else:
        # Create a wiki
        wiki_page = WikiPage.objects.create_for_node(node, wiki_name, data, auth, parent_wiki_id, True)
        updated_wiki_id = wiki_page.id
        ret = {'status': 'success', 'path': path}
    return ret, updated_wiki_id

def _import_same_level_wiki(wiki_info, depth, auth, node, task):
    if task.is_aborted():
        raise ImportTaskAborted
    ret = []
    wiki_id_list = []
    for info in wiki_info:
        slash_ctn = info['path'].count('/')
        wiki_depth = slash_ctn - 1
        if depth == wiki_depth:
            try:
                res, wiki_id = _wiki_import_create_or_update(info['path'], info['wiki_content'], auth, node, task, info['parent_wiki_name'])
                ret.append(res)
                wiki_id_list.append(wiki_id)
            except ImportTaskAborted:
                logger.info('Wiki import task aborted when import child wiki page.')
                return ret, wiki_id_list
            except Exception as err:
                logger.error(err)
    return ret, wiki_id_list

@must_be_valid_project
@must_have_permission(ADMIN)
def project_get_task_result(task_id, node, **kwargs):
    res = AsyncResult(task_id,app=celery_app)
    result = None
    if not res.ready():
        return None
    try:
        result = res.get()
    except Exception as err:
        err_msg = wiki_utils.extract_err_msg(err)
        raise HTTPError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, data=dict(
            message_long=err_msg
        ))
    return result

@must_be_valid_project
@must_have_permission(ADMIN)
def project_clean_celery_tasks(node, **kwargs):
    qs_alive_task = WikiImportTask.objects.filter(status=WikiImportTask.STATUS_RUNNING, node=node)
    alive_task_ids = WikiImportTask.objects.values_list('task_id').filter(status=WikiImportTask.STATUS_RUNNING, node=node)[0]
    for task_id in alive_task_ids:
        task = AbortableAsyncResult(task_id, app=celery_app)
        task.abort()
    qs_alive_task.update(status=WikiImportTask.STATUS_STOPPED)

@must_be_valid_project
@must_have_permission(ADMIN)
def project_get_abort_wiki_import_result(node, **kwargs):
    result = None
    process_end_list = WikiImportTask.objects.values_list('process_end', flat=True).filter(status=WikiImportTask.STATUS_STOPPED, node=node)
    if None not in process_end_list:
        return { 'aborted' : True}
    return result

def check_running_task(task_id, node):
    running_task_ctn = WikiImportTask.objects.filter(node=node, status=WikiImportTask.STATUS_RUNNING).count()
    if running_task_ctn > 1:
        if task_id:
            change_task_status(task_id, WikiImportTask.STATUS_ERROR, True)
        raise WIKI_IMPORT_TASK_ALREADY_EXISTS

def change_task_status(task_id, status, set_process_end):
    task = WikiImportTask.objects.get(task_id=task_id)
    task.status = status
    if set_process_end:
        process_end = timezone.make_naive(timezone.now(), timezone.utc)
        task.process_end = process_end
    task.save()

def set_wiki_import_task_proces_end(node):
    qs_alive_task = WikiImportTask.objects.filter(process_end__isnull=True, status=WikiImportTask.STATUS_STOPPED, node=node)
    process_end = timezone.make_naive(timezone.now(), timezone.utc)
    qs_alive_task.update(process_end=process_end)

@must_be_valid_project  # returns project
@must_have_addon('wiki', 'node')
def project_update_wiki_page_sort(node, **kwargs):
    data = request.get_json()
    sorted_data = data['sortedData']
    sort_id_list, sort_num_list, sort_parent_wiki_id_list  = _get_sorted_list(sorted_data, None)
    _bulk_update_wiki_sort(node, sort_id_list, sort_num_list, sort_parent_wiki_id_list)

def _get_sorted_list(sorted_data, parent_wiki_id):
    id_list = []
    sort_list = []
    parent_wiki_id_list = []
    child_id_list = []
    child_sort_list = []
    child_parent_wiki_id_list = []
    for data in sorted_data:
        id_list.append(data['id'])
        sort_list.append(data['sortOrder'])
        parent_wiki_id_list.append(parent_wiki_id)
        if len(data['children']) > 0:
            child_id_list, child_sort_list, child_parent_wiki_id_list = _get_sorted_list(data['children'], data['id'])
            id_list.extend(child_id_list)
            sort_list.extend(child_sort_list)
            parent_wiki_id_list.extend(child_parent_wiki_id_list)
    return id_list, sort_list, parent_wiki_id_list

def _bulk_update_wiki_sort(node, sort_id_list, sort_num_list, parent_wiki_id_list):
    wiki_pages = node.wikis.filter(deleted__isnull=True).exclude(page_name='home')

    for page in wiki_pages:
        idx = sort_id_list.index(page._primary_key)
        sort_order_number = sort_num_list[idx]
        parent_wiki_id = parent_wiki_id_list[idx]
        setattr(page, 'sort_order', sort_order_number)
        if parent_wiki_id is not None:
            parent_id = WikiPage.objects.get(guids___id=parent_wiki_id).id
            setattr(page, 'parent', parent_id)
        else:
            setattr(page, 'parent', None)
    bulk_update(wiki_pages)
