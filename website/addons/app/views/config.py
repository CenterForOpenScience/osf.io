from __future__ import unicode_literals

import httplib as http

from flask import request

from framework.exceptions import HTTPError

from website.project.decorators import must_have_addon
from website.project.decorators import must_be_contributor_or_public


# GET
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def app_get_default_sort_key(node_addon, **kwargs):
    return {
        'keys': sorted(node_addon.mapping.keys()),
        'selected': node_addon.default_sort,
    }


# POST
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def app_set_default_sort_key(node_addon, **kwargs):
    sort_key = request.get_json().get('key')
    # Allow having no default sort key
    if not sort_key:
        # None is prefable to empty string
        node_addon.default_sort = None
    else:
        if sort_key not in node_addon.mapping.keys():
            raise HTTPError(http.BAD_REQUEST)

        node_addon.default_sort = sort_key

    node_addon.save()
