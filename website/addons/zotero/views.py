"""

"""

import httplib as http

from flask import request

from framework.exceptions import HTTPError

from website.project.decorators import must_be_contributor
from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon
from website.project.views.node import _view_project


@must_be_contributor
def zotero_set_config(**kwargs):

    node = kwargs.get('node') or kwargs.get('project')
    zotero = node.get_addon('zotero')
    if zotero:
        zotero.zotero_id = request.json.get('zotero_id', '')
        zotero.save()
    else:
        raise HTTPError(http.BAD_REQUEST)


@must_be_contributor_or_public
@must_have_addon('zotero', 'node')
def zotero_widget(*args, **kwargs):
    node = kwargs['node'] or kwargs['project']
    zotero = node.get_addon('zotero')
    summary = zotero._summarize_references()
    rv = {
        'complete': bool(summary),
        'summary': summary,
    }
    rv.update(zotero.config.to_json())
    return rv


@must_be_contributor_or_public
def zotero_page(**kwargs):

    auth = kwargs['auth']
    node = kwargs['node'] or kwargs['project']
    zotero = node.get_addon('zotero')

    data = _view_project(node, auth)

    xml = zotero._fetch_references()

    rv = {
        'complete': True,
        'xml': xml,
        'addon_page_js': zotero.config.include_js['page'],
        'addon_page_css': zotero.config.include_css['page'],
    }
    rv.update(data)
    return rv
