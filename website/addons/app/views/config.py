from __future__ import unicode_literals

import httplib as http

from flask import request

from framework.exceptions import HTTPError

from website.search import search
from website.search.exceptions import IndexNotFoundError
from website.project.decorators import must_have_addon
from website.project.decorators import must_have_permission
from website.project.decorators import must_be_contributor_or_public

from website.addons.app.utils import args_to_query
from website.addons.app.utils import elastic_to_rss


# GET
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def app_get_default_sort_key(node_addon, **kwargs):
    try:
        keys = search.get_mapping('metadata', node_addon.namespace).keys()
    except IndexNotFoundError:
        keys = []

    return {
        'keys': keys,
        'selected': node_addon.default_sort,
    }


# POST
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def app_set_default_sort_key(node_addon, **kwargs):
    data = request.get_json()
    sort_key = data.get('key')
    if sort_key not in search.get_mapping('metadata', node_addon.namespace).keys():
        raise HTTPError(http.BAD_REQUEST)

    node_addon.default_sort = sort_key
    node_addon.save()
