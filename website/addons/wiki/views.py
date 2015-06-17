# -*- coding: utf-8 -*-

import httplib as http
import logging

from bs4 import BeautifulSoup
from flask import request

from framework.mongo.utils import to_mongo_key
from framework.exceptions import HTTPError
from framework.auth.utils import privacy_info_handle
from framework.flask import redirect

from website.addons.wiki import settings
from website.addons.wiki import utils as wiki_utils
from website.profile.utils import get_gravatar
from website.project.views.node import _view_project
from website.project.model import has_anonymous_link
from website.project.decorators import (
    must_be_contributor_or_public,
    must_have_addon, must_not_be_registration,
    must_be_valid_project,
    must_have_permission,
)

from .exceptions import (
    NameEmptyError,
    NameInvalidError,
    NameMaximumLengthError,
    PageCannotRenameError,
    PageConflictError,
    PageNotFoundError,
    InvalidVersionError,
)
from .model import NodeWikiPage

logger = logging.getLogger(__name__)


WIKI_NAME_EMPTY_ERROR = HTTPError(http.BAD_REQUEST, data=dict(
    message_short='Invalid request',
    message_long='The wiki page name cannot be empty.'
))
WIKI_NAME_MAXIMUM_LENGTH_ERROR = HTTPError(http.BAD_REQUEST, data=dict(
    message_short='Invalid request',
    message_long='The wiki page name cannot be more than 100 characters.'
))
WIKI_PAGE_CANNOT_RENAME_ERROR = HTTPError(http.BAD_REQUEST, data=dict(
    message_short='Invalid request',
    message_long='The wiki page cannot be renamed.'
))
WIKI_PAGE_CONFLICT_ERROR = HTTPError(http.CONFLICT, data=dict(
    message_short='Page conflict',
    message_long='A wiki page with that name already exists.'
))
WIKI_PAGE_NOT_FOUND_ERROR = HTTPError(http.NOT_FOUND, data=dict(
    message_short='Not found',
    message_long='A wiki page could not be found.'
))
WIKI_INVALID_VERSION_ERROR = HTTPError(http.BAD_REQUEST, data=dict(
    message_short='Invalid request',
    message_long='The requested version of this wiki page does not exist.'
))


def _get_wiki_versions(node, name, anonymous=False):
    key = to_mongo_key(name)

    # Skip if wiki_page doesn't exist; happens on new projects before
    # default "home" page is created
    if key not in node.wiki_pages_versions:
        return []

    versions = [
        NodeWikiPage.load(version_wiki_id)
        for version_wiki_id in node.wiki_pages_versions[key]
    ]

    return [
        {
            'version': version.version,
            'user_fullname': privacy_info_handle(version.user.fullname, anonymous, name=True),
            'date': version.date.replace(microsecond=0).isoformat(),
        }
        for version in reversed(versions)
    ]


def _get_wiki_pages_current(node):
    return [
        {
            'name': sorted_page.page_name,
            'url': node.web_url_for('project_wiki_view', wname=sorted_page.page_name, _guid=True)
        }
        for sorted_page in [
            node.get_wiki_page(sorted_key)
            for sorted_key in sorted(node.wiki_pages_current)
        ]
        # TODO: remove after forward slash migration
        if sorted_page is not None
    ]


def _get_wiki_api_urls(node, name, additional_urls=None):
    urls = {
        'base': node.api_url_for('project_wiki_home'),
        'delete': node.api_url_for('project_wiki_delete', wname=name),
        'rename': node.api_url_for('project_wiki_rename', wname=name),
        'content': node.api_url_for('wiki_page_content', wname=name),
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


def _serialize_wiki_toc(project, auth):
    toc = [
        {
            'id': child._primary_key,
            'title': child.title,
            'category': child.category,
            'pages_current': _get_wiki_pages_current(child),
            'url': child.web_url_for('project_wiki_view', wname='home', _guid=True),
            'is_pointer': not child.primary,
            'link': auth.private_key
        }
        for child in project.nodes
        if not child.is_deleted
        and child.can_view(auth)
        if child.has_addon('wiki')
    ]
    return toc


@must_be_contributor_or_public
@must_have_addon('wiki', 'node')
def wiki_widget(**kwargs):
    node = kwargs['node'] or kwargs['project']
    wiki = node.get_addon('wiki')
    wiki_page = node.get_wiki_page('home')

    more = False
    use_python_render = False
    if wiki_page and wiki_page.html(node):
        wiki_html = wiki_page.html(node)
        if len(wiki_html) > 500:
            wiki_html = BeautifulSoup(wiki_html[:500] + '...', 'html.parser')
            more = True
        else:
            wiki_html = BeautifulSoup(wiki_html)
            more = False
        use_python_render = wiki_page.rendered_before_update
    else:
        wiki_html = None

    ret = {
        'complete': True,
        'wiki_content': unicode(wiki_html) if wiki_html else None,
        'wiki_content_url': node.api_url_for('wiki_page_content', wname='home'),
        'use_python_render': use_python_render,
        'more': more,
        'include': False,
    }
    ret.update(wiki.config.to_json())
    return ret


@must_be_valid_project
@must_have_permission('write')
@must_have_addon('wiki', 'node')
def wiki_page_draft(wname, **kwargs):
    node = kwargs['node'] or kwargs['project']
    wiki_page = node.get_wiki_page(wname)

    return {
        'wiki_content': wiki_page.content if wiki_page else None,
        'wiki_draft': (wiki_page.get_draft(node) if wiki_page
                       else wiki_utils.get_sharejs_content(node, wname)),
    }


@must_be_valid_project
@must_be_contributor_or_public
@must_have_addon('wiki', 'node')
def wiki_page_content(wname, wver=None, **kwargs):
    node = kwargs['node'] or kwargs['project']
    wiki_page = node.get_wiki_page(wname, version=wver)
    use_python_render = wiki_page.rendered_before_update if wiki_page else False

    return {
        'wiki_content': wiki_page.content if wiki_page else '',
        # Only return rendered version if page was saved before wiki change
        'wiki_rendered': wiki_page.html(node) if use_python_render else '',
    }


@must_be_valid_project  # injects project
@must_have_permission('write')  # injects user, project
@must_not_be_registration
@must_have_addon('wiki', 'node')
def project_wiki_delete(auth, wname, **kwargs):
    node = kwargs['node'] or kwargs['project']
    wiki_name = wname.strip()
    wiki_page = node.get_wiki_page(wiki_name)
    sharejs_uuid = wiki_utils.get_sharejs_uuid(node, wiki_name)

    if not wiki_page:
        raise HTTPError(http.NOT_FOUND)
    node.delete_node_wiki(wiki_name, auth)
    wiki_utils.broadcast_to_sharejs('delete', sharejs_uuid, node)
    return {}


@must_be_valid_project  # returns project
@must_be_contributor_or_public
@must_have_addon('wiki', 'node')
def project_wiki_view(auth, wname, path=None, **kwargs): #GRUMBLE
    node = kwargs['node'] or kwargs['project']
    anonymous = has_anonymous_link(node, auth)
    wiki_name = (wname or '').strip()
    wiki_key = to_mongo_key(wiki_name)
    wiki_page = node.get_wiki_page(wiki_name)
    toc = _serialize_wiki_toc(node, auth=auth)
    can_edit = True #node.has_permission(auth.user, 'write') or True and not node.is_registration #GRUMBLE
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

    # Default versions for view and compare
    version_settings = {
        'view': view or ('preview' if 'edit' in panels_used else 'current'),
        'compare': compare or 'previous',
    }

    # ensure home is always lower case since it cannot be renamed
    if wiki_name.lower() == 'home':
        wiki_name = 'home'

    if wiki_page:
        version = wiki_page.version
        is_current = wiki_page.is_current
        content = wiki_page.html(node)
        use_python_render = wiki_page.rendered_before_update
    else:
        version = 'NA'
        is_current = False
        content = ''
        use_python_render = False

    if can_edit:
        if wiki_key not in node.wiki_private_uuids:
            wiki_utils.generate_private_uuid(node, wiki_name)
        sharejs_uuid = wiki_utils.get_sharejs_uuid(node, wiki_name)
    else:
        if wiki_key not in node.wiki_pages_current and wiki_key != 'home':
            raise WIKI_PAGE_NOT_FOUND_ERROR
        if 'edit' in request.args:
            raise HTTPError(http.FORBIDDEN)
        sharejs_uuid = None

    ret = {
        'wiki_id': wiki_page._primary_key if wiki_page else None,
        'wiki_name': wiki_page.page_name if wiki_page else wiki_name,
        'wiki_content': content,
        'use_python_render': use_python_render,
        'page': wiki_page,
        'version': version,
        'versions': versions,
        'sharejs_uuid': sharejs_uuid or '',
        'sharejs_url': settings.SHAREJS_URL,
        'is_current': is_current,
        'version_settings': version_settings,
        'pages_current': _get_wiki_pages_current(node),
        'toc': toc,
        'category': node.category,
        'panels_used': panels_used,
        'num_columns': num_columns,
        'urls': {
            'api': _get_wiki_api_urls(node, wiki_name, {
                'content': node.api_url_for('wiki_page_content', wname=wiki_name),
                'draft': node.api_url_for('wiki_page_draft', wname=wiki_name),
            }),
            'web': _get_wiki_web_urls(node, wiki_name),
            'gravatar': get_gravatar(auth.user, 25),
        },
    }
    ret.update(_view_project(node, auth, primary=True))
    return ret


@must_be_valid_project  # injects node or project
@must_have_permission('write')  # injects user
@must_not_be_registration
@must_have_addon('wiki', 'node')
def project_wiki_edit_post(auth, wname, **kwargs):
    node = kwargs['node'] or kwargs['project']
    wiki_name = wname.strip()
    wiki_page = node.get_wiki_page(wiki_name)
    redirect_url = node.web_url_for('project_wiki_view', wname=wiki_name, _guid=True)
    form_wiki_content = request.form['content']

    # ensure home is always lower case since it cannot be renamed
    if wiki_name.lower() == 'home':
        wiki_name = 'home'

    if wiki_page:
        # Only update node wiki if content has changed
        if form_wiki_content != wiki_page.content:
            node.update_node_wiki(wiki_page.page_name, form_wiki_content, auth)
            ret = {'status': 'success'}
        else:
            ret = {'status': 'unmodified'}
    else:
        # update_node_wiki will create a new wiki page because a page
        node.update_node_wiki(wiki_name, form_wiki_content, auth)
        ret = {'status': 'success'}
    return ret, http.FOUND, None, redirect_url


@must_be_valid_project
@must_have_addon('wiki', 'node')
def project_wiki_home(**kwargs):
    node = kwargs['node'] or kwargs['project']
    return redirect(node.web_url_for('project_wiki_view', wname='home', _guid=True))


@must_be_valid_project  # injects project
@must_be_contributor_or_public
@must_have_addon('wiki', 'node')
def project_wiki_id_page(auth, wid, **kwargs):
    node = kwargs['node'] or kwargs['project']
    wiki_page = node.get_wiki_page(id=wid)
    if wiki_page:
        return redirect(node.web_url_for('project_wiki_view', wname=wiki_page.page_name, _guid=True))
    else:
        raise WIKI_PAGE_NOT_FOUND_ERROR


@must_be_valid_project
@must_have_permission('write') #GRUMBLE
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
@must_have_permission('write')
@must_have_addon('wiki', 'node')
def project_wiki_rename(auth, wname, **kwargs):
    """View that handles user the X-editable input for wiki page renaming.

    :param wname: The target wiki page name.
    :param-json value: The new wiki page name.
    """
    node = kwargs['node'] or kwargs['project']
    wiki_name = wname.strip()
    new_wiki_name = request.get_json().get('value', None)

    try:
        node.rename_node_wiki(wiki_name, new_wiki_name, auth)
    except NameEmptyError:
        raise WIKI_NAME_EMPTY_ERROR
    except NameInvalidError as error:
        raise HTTPError(http.BAD_REQUEST, data=dict(
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
    else:
        sharejs_uuid = wiki_utils.get_sharejs_uuid(node, new_wiki_name)
        wiki_utils.broadcast_to_sharejs('redirect', sharejs_uuid, node, new_wiki_name)


@must_be_valid_project  # returns project
@must_have_permission('write')  # returns user, project
@must_not_be_registration
@must_have_addon('wiki', 'node')
def project_wiki_validate_name(wname, **kwargs):
    node = kwargs['node'] or kwargs['project']
    wiki_name = wname.strip()
    wiki_key = to_mongo_key(wiki_name)

    if wiki_key in node.wiki_pages_current or wiki_key == 'home':
        raise HTTPError(http.CONFLICT, data=dict(
            message_short='Wiki page name conflict.',
            message_long='A wiki page with that name already exists.'
        ))
    return {'message': wiki_name}
