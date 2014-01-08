"""

"""

import httplib as http

from framework import request
from framework.exceptions import HTTPError

from website.project.decorators import must_be_contributor
from website.project.decorators import must_be_contributor_or_public
from website.project.views.node import _view_project


@must_be_contributor
def zotero_settings(**kwargs):

    node = kwargs.get('node') or kwargs.get('project')
    addons = node.addonzoterosettings__addons
    if addons:
        zotero = addons[0]
        zotero.zotero_id = request.json.get('zotero_id', '')
        zotero.save()
    else:
        raise HTTPError(http.BAD_REQUEST)


@must_be_contributor_or_public
def zotero_page(**kwargs):

    user = kwargs.get('user')
    node = kwargs.get('node') or kwargs.get('project')
    addons = node.addonzoterosettings__addons
    if addons:
        zotero = addons[0]
        rv = {
            'addon_title': 'Zotero',
            'addon_page': zotero.render_page(),
        }
        rv.update(_view_project(node, user))
        return rv
    else:
        raise HTTPError(http.BAD_REQUEST)

