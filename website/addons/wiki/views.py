# -*- coding: utf-8 -*-

import difflib
import httplib as http
import logging

from bs4 import BeautifulSoup
from flask import request

from framework import status
from framework.forms.utils import sanitize
from framework.mongo.utils import from_mongo
from framework.exceptions import HTTPError
from framework.auth.utils import privacy_info_handle

from website.project.views.node import _view_project
from website.project import show_diff
from website.project.model import has_anonymous_link
from website.project.decorators import (
    must_be_contributor_or_public,
    must_have_addon, must_not_be_registration,
    must_be_valid_project,
    must_have_permission
)

from .model import NodeWikiPage

logger = logging.getLogger(__name__)

HOME = 'home'


@must_be_contributor_or_public
@must_have_addon('wiki', 'node')
def wiki_widget(**kwargs):
    node = kwargs['node'] or kwargs['project']
    wiki = node.get_addon('wiki')
    wiki_page = node.get_wiki_page('home')

    more = False
    if wiki_page and wiki_page.html(node):
        wiki_html = wiki_page.html(node)
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
        'include': False,
    }
    rv.update(wiki.config.to_json())
    return rv


@must_be_valid_project
@must_have_addon('wiki', 'node')
def project_wiki_home(**kwargs):
    node = kwargs['node'] or kwargs['project']
    return {}, None, None, '{}wiki/home/'.format(node.url)


def _get_wiki_versions(node, wid, anonymous=False):

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
            'user_fullname': privacy_info_handle(
                version.user.fullname, anonymous, name=True
            ),
            'date': version.date.replace(microsecond=0),
        }
        for version in reversed(versions)
    ]


@must_be_valid_project  # injects project
@must_be_contributor_or_public  # injects user, project
@must_have_addon('wiki', 'node')
def project_wiki_compare(auth, wid, compare_id, **kwargs):
    node = kwargs['node'] or kwargs['project']

    anonymous = has_anonymous_link(node, auth)
    wiki_page = node.get_wiki_page(wid)
    toc = serialize_wiki_toc(node, auth=auth)

    if not wiki_page:
        wiki_page = NodeWikiPage()

    comparison_page = node.get_wiki_page(wid, compare_id)
    if comparison_page:
        current = wiki_page.content
        comparison = comparison_page.content
        sm = difflib.SequenceMatcher(None, comparison, current)
        content = show_diff(sm)
        content = content.replace('\n', '<br />')
        ret = {
            'pageName': wid,
            'wiki_content': content,
            'wiki_id': wiki_page._primary_key if wiki_page else None,
            'versions': _get_wiki_versions(node, wid, anonymous),
            'is_current': True,
            'is_edit': True,
            'version': wiki_page.version,
            'pages_current': [
                from_mongo(version)
                for version in node.wiki_pages_current
            ],
            'toc': toc,
            'url': node.url,
            'api_url': node.api_url,
            'category': node.category
        }
        ret.update(_view_project(node, auth, primary=True))
        return ret

    raise HTTPError(http.NOT_FOUND)


@must_be_valid_project  # injects project
@must_have_permission('write')  # injects auth, project
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
            'wiki_content': wiki_page.html(node),
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
            'pages': sorted(child.wiki_pages_current.keys()) if child.wiki_pages_current else [],
            'url': child.web_url_for('project_wiki_page', wid=HOME),
            'is_pointer': not child.primary,
            'link': auth.private_key
        }
        for child in project.nodes
        if not child.is_deleted
        and child.can_view(auth)
        if child.has_addon('wiki')
    ]
    return toc


@must_be_valid_project  # injects project
@must_be_contributor_or_public
@must_have_addon('wiki', 'node')
def project_wiki_page(auth, **kwargs):

    wid = kwargs['wid']
    node = kwargs['node'] or kwargs['project']
    anonymous = has_anonymous_link(node, auth)
    wiki_page = node.get_wiki_page(wid)

    # todo breaks on /<script>; why?

    if wiki_page:
        version = wiki_page.version
        is_current = wiki_page.is_current
        content = wiki_page.html(node)
    else:
        version = 'NA'
        is_current = False
        content = '<p><em>No wiki content</em></p>'

    toc = serialize_wiki_toc(node, auth=auth)

    ret = {
        'wiki_id': wiki_page._primary_key if wiki_page else None,
        'pageName': wid,
        'page': wiki_page,
        'version': version,
        'versions': _get_wiki_versions(node, wid, anonymous=anonymous),
        'wiki_content': content,
        'is_current': is_current,
        'is_edit': False,
        'pages_current': sorted([
            from_mongo(each)
            for each in node.wiki_pages_current
        ]),
        'toc': toc,
        'url': node.url,
        'api_url': node.api_url,
        'category': node.category
    }

    ret.update(_view_project(node, auth, primary=True))
    return ret


@must_be_valid_project
@must_be_contributor_or_public
@must_have_addon('wiki', 'node')
def wiki_page_content(wid, **kwargs):
    node = kwargs['node'] or kwargs['project']

    wiki_page = node.get_wiki_page(wid)

    return {
        'wiki_content': wiki_page.content if wiki_page else ''
    }


@must_be_valid_project  # returns project
@must_have_permission('write')  # returns user, project
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
        wiki_page = NodeWikiPage()
        version = 'NA'
        is_current = False
        content = ''

    if wiki_page.share_uuid is None:
        wiki_page.generate_share_uuid()

    toc = serialize_wiki_toc(node, auth=auth)
    rv = {
        'pageName': wid,
        'page': wiki_page,
        'version': version,
        'versions': _get_wiki_versions(node, wid),
        'wiki_content': content,
        'wiki_id': wiki_page._primary_key if wiki_page else None,
        'share_uuid': wiki_page.share_uuid,
        'is_current': is_current,
        'is_edit': True,
        'pages_current': [
            from_mongo(each)
            for each in node.wiki_pages_current
        ],
        'toc': toc,
        'url': node.url,
        'api_url': node.api_url,
        'category': node.category
    }
    rv.update(_view_project(node, auth, primary=True))
    return rv


@must_be_valid_project  # injects node or project
@must_have_permission('write')  # injects user
@must_not_be_registration
@must_have_addon('wiki', 'node')
def project_wiki_edit_post(wid, auth, **kwargs):

    node_to_use = kwargs['node'] or kwargs['project']

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
            'status': 'success',
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

@must_be_valid_project  # injects project
@must_have_permission('write')  # injects user, project
@must_not_be_registration
@must_have_addon('wiki', 'node')
def project_wiki_delete(auth, wid, **kwargs):
    node = kwargs['node'] or kwargs['project']
    page = NodeWikiPage.load(wid)
    node.delete_node_wiki(node, page, auth)
    node.save()
    return {}
