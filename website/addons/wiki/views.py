"""

"""
import logging
import httplib as http
import difflib

from bs4 import BeautifulSoup

from framework import request, status, url_for
from framework.forms.utils import sanitize
from framework.mongo.utils import from_mongo
from framework.exceptions import HTTPError
from website.project.views.node import _view_project
from website.project import show_diff
from website.project.decorators import (
    must_be_contributor_or_public,
    must_have_addon, must_not_be_registration,
    must_be_valid_project,
    must_have_permission
)

from .model import NodeWikiPage

logger = logging.getLogger(__name__)

HOME = 'home'


def get_wiki_url(node, page=HOME):
    """Get the URL for the wiki page for a node or pointer."""
    view_spec = 'OsfWebRenderer__project_wiki_page'
    if node.category != 'project':
        pid = node.parent_node._id
        nid = node._id
        return url_for(view_spec, pid=pid, nid=nid, wid=page)
    else:
        if not node.primary:
            pid = node.node._id
        else:
            pid = node._id
        return url_for(view_spec, pid=pid, wid=page)


@must_be_contributor_or_public
@must_have_addon('wiki', 'node')
def wiki_widget(**kwargs):
    node = kwargs['node'] or kwargs['project']
    wiki = node.get_addon('wiki')
    wiki_page = node.get_wiki_page('home')

    more = False
    if wiki_page and wiki_page.html:
        wiki_html = wiki_page.html
        if len(wiki_html) > 500:
            wiki_html = BeautifulSoup(wiki_html[:500] + '...', 'html.parser')
            more = True
        else:
            wiki_html = BeautifulSoup(wiki_html)
            more = False
    else:
        wiki_html = None

    rv = {
        'complete': True,
        'content': wiki_html,
        'more': more,
    }
    rv.update(wiki.config.to_json())
    return rv


@must_be_valid_project
@must_have_addon('wiki', 'node')
def project_wiki_home(**kwargs):
    node = kwargs['node'] or kwargs['project']
    return {}, None, None, '{}wiki/home/'.format(node.url)


def _get_wiki_versions(node, wid):

    # Skip if page doesn't exist; happens on new projects before
    # default "home" page is created
    if wid not in node.wiki_pages_versions:
        return []

    versions = [
        NodeWikiPage.load(page)
        for page in node.wiki_pages_versions[wid]
    ]

    return [
        {
            'version': version.version,
            'user_fullname': version.user.fullname,
            'date': version.date.replace(microsecond=0),
        }
        for version in reversed(versions)
    ]


@must_be_valid_project # returns project
@must_be_contributor_or_public # returns user, project
@must_have_addon('wiki', 'node')
def project_wiki_compare(auth, **kwargs):
    node = kwargs['node'] or kwargs['project']
    wid = kwargs['wid']

    wiki_page = node.get_wiki_page(wid)

    if wiki_page:
        compare_id = kwargs['compare_id']
        comparison_page = node.get_wiki_page(wid, compare_id)
        if comparison_page:
            current = wiki_page.content
            comparison = comparison_page.content
            sm = difflib.SequenceMatcher(None, comparison, current)
            content = show_diff(sm)
            content = content.replace('\n', '<br />')
            rv = {
                'pageName': wid,
                'wiki_content': content,
                'versions': _get_wiki_versions(node, wid),
                'is_current': True,
                'is_edit': True,
                'version': wiki_page.version,
            }
            rv.update(_view_project(node, auth, primary=True))
            return rv
    raise HTTPError(http.NOT_FOUND)


@must_be_valid_project # returns project
@must_have_permission('write') # returns user, project
@must_have_addon('wiki', 'node')
def project_wiki_version(auth, **kwargs):
    node = kwargs['node'] or kwargs['project']
    wid = kwargs['wid']
    vid = kwargs['vid']

    wiki_page = node.get_wiki_page(wid, version=vid)

    if wiki_page:
        rv = {
            'wiki_id': wiki_page._id if wiki_page else None,
            'pageName': wid,
            'wiki_content': wiki_page.html,
            'version': wiki_page.version,
            'is_current': wiki_page.is_current,
            'is_edit': False,
        }
        rv.update(_view_project(node, auth, primary=True))
        return rv

    raise HTTPError(http.NOT_FOUND)


def serialize_wiki_toc(project, auth):
    toc = [
        {
            'id': child._primary_key,
            'title': child.title,
            'category': child.category,
            'pages': child.wiki_pages_current.keys() if child.wiki_pages_current else [],
            'url': get_wiki_url(child, page=HOME),
            'is_pointer': not child.primary,
            'link': auth.private_key
        }
        for child in project.nodes
        if not child.is_deleted
        and child.can_view(auth)
        if child.has_addon('wiki')
    ]
    return toc


@must_be_valid_project # returns project
@must_be_contributor_or_public
@must_have_addon('wiki', 'node')
def project_wiki_page(auth, **kwargs):

    wid = kwargs['wid']
    node = kwargs['node'] or kwargs['project']

    wiki_page = node.get_wiki_page(wid)

    # todo breaks on /<script>; why?

    if wiki_page:
        version = wiki_page.version
        is_current = wiki_page.is_current
        content = wiki_page.html
    else:
        version = 'NA'
        is_current = False
        content = '<p><em>No wiki content</em></p>'

    toc = serialize_wiki_toc(node, auth=auth)

    rv = {
        'wiki_id': wiki_page._primary_key if wiki_page else None,
        'pageName': wid,
        'page': wiki_page,
        'version': version,
        'wiki_content': content,
        'is_current': is_current,
        'is_edit': False,
        'pages_current': [
            from_mongo(version)
            for version in node.wiki_pages_versions
        ],
        'toc': toc,
        'url': node.url,
        'api_url': node.api_url,
        'category': node.category
    }

    rv.update(_view_project(node, auth, primary=True))
    return rv


@must_be_valid_project # returns project
@must_have_permission('write') # returns user, project
@must_not_be_registration
@must_have_addon('wiki', 'node')
def project_wiki_edit(auth, **kwargs):
    wid = kwargs['wid']
    node = kwargs['node'] or kwargs['project']
    wiki_page = node.get_wiki_page(wid)

    if wiki_page:
        version = wiki_page.version
        is_current = wiki_page.is_current
        content = wiki_page.content
    else:
        version = 'NA'
        is_current = False
        content = ''
    rv = {
        'pageName': wid,
        'page': wiki_page,
        'version': version,
        'versions': _get_wiki_versions(node, wid),
        'wiki_content': content,
        'is_current': is_current,
        'is_edit': True,
    }
    rv.update(_view_project(node, auth, primary=True))
    return rv


@must_be_valid_project # returns project
@must_have_permission('write') # returns user, project
@must_not_be_registration
@must_have_addon('wiki', 'node')
def project_wiki_edit_post(auth, **kwargs):

    node_to_use = kwargs['node'] or kwargs['project']
    user = auth.user
    wid = kwargs['wid']
    logging.debug(
        '{user} edited wiki page: {wid}'.format(
            user=user.username, wid=wid
        )
    )

    if wid != sanitize(wid):
        status.push_status_message("This is an invalid wiki page name")
        raise HTTPError(http.BAD_REQUEST, redirect_url='{}wiki/'.format(node_to_use.url))

    wiki_page = node_to_use.get_wiki_page(wid)

    if wiki_page:
        content = wiki_page.content
    else:
        content = ''
    if request.form['content'] != content:
        node_to_use.update_node_wiki(wid, request.form['content'], auth)
        return {
            'status' : 'success',
        }, None, None, '{}wiki/{}/'.format(node_to_use.url, wid)
    else:
        return {}, None, None, '{}wiki/{}/'.format(node_to_use.url, wid)


@must_not_be_registration
@must_have_permission('write')
@must_have_addon('wiki', 'node')
def project_wiki_rename(**kwargs):
    node = kwargs['node'] or kwargs['project']
    wid = request.json.get('pk', None)
    page = NodeWikiPage.load(wid)
    new_name = request.json.get('value', None)
    if new_name != sanitize(new_name):
        raise HTTPError(http.UNPROCESSABLE_ENTITY)

    if page and new_name:
        try:
            exist_check = node.wiki_pages_versions[new_name.lower()]
        except KeyError:
            exist_check = None
        if exist_check:
            raise HTTPError(http.CONFLICT)

        node.wiki_pages_versions[new_name.lower()] = node.wiki_pages_versions[page.page_name.lower()]
        del node.wiki_pages_versions[page.page_name.lower()]
        node.wiki_pages_current[new_name.lower()] = node.wiki_pages_current[page.page_name.lower()]
        del node.wiki_pages_current[page.page_name.lower()]
        node.save()
        page.rename(new_name)
        return {'message': new_name}

    raise HTTPError(http.BAD_REQUEST)
