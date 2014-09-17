from __future__ import unicode_literals

import httplib as http

from flask import request

from framework.exceptions import HTTPError

from website.search.search import search
from website.project.decorators import (
    must_be_valid_project,
    must_have_addon, must_have_permission,
    must_not_be_registration, must_be_contributor_or_public
)


# GET
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def list_custom_routes(node_addon, **kwargs):
    node = kwargs.get('node') or kwargs['project']

    return {
        node.api_url_for('resolve_route', route=url): query
        for url, query
        in node_addon.custom_routes.items()
    }


# GET
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def resolve_route(node_addon, route, **kwargs):
    start = request.args.get('page', 0)

    try:
        route = node_addon[route]
    except KeyError:
        raise HTTPError(http.NOT_FOUND)

    ret = search(route, _type=node_addon.namespace, index='metadata', start=start)

    return {
        'results': ret['hits']['hits'],
        'total': ret['hits']['total']
    }


# POST
@must_have_permission('admin')
@must_have_addon('app', 'node')
def create_route(node_addon, **kwargs):
    route = request.json.get('route')
    query = request.json.get('query')
    exists = node_addon.get(route) is not None

    if not route or not query or exists:
        raise HTTPError(http.BAD_REQUEST)

    node_addon[route] = query
    return http.CREATED


# PUT
@must_have_permission('admin')
@must_have_addon('app', 'node')
def update_route(node_addon, route, **kwargs):
    query = request.json.get('query')

    if not route or query:
        raise HTTPError(http.BAD_REQUEST)

    created = not node_addon.get(route)
    node_addon[route] = query

    if created:
        return http.CREATED


# DELETE
@must_have_permission('admin')
@must_have_addon('app', 'node')
def delete_route(node_addon, route, **kwargs):
    if not node_addon.custom_routes.get(route):
        raise HTTPError(http.BAD_REQUEST)

    del node_addon.custom_routes[route]
    node_addon.save()

    return http.NO_CONTENT
