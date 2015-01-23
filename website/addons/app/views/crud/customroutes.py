from __future__ import unicode_literals

import httplib as http

from flask import request

from framework.exceptions import HTTPError

from website.search.search import search

from website.project.decorators import must_have_addon
from website.project.decorators import must_have_permission
from website.project.decorators import must_be_contributor_or_public

from website.addons.app.utils import elastic_to_rss


# GET
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def list_custom_routes(node_addon, **kwargs):
    node = kwargs.get('node') or kwargs['project']

    return {
        query: node.api_url_for('resolve_route', route=url)
        for url, query
        in node_addon.routes.items()
    }


# GET
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def resolve_route(node_addon, route, **kwargs):
    size = request.args.get('size')
    start = request.args.get('from')

    try:
        route = node_addon.routes[route]
    except KeyError:
        raise HTTPError(http.NOT_FOUND)

    q = node_addon.build_query(route, size, start)

    return search(q, doc_type=node_addon.namespace, index='metadata')


# GET
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def resolve_route_rss(node_addon, route, **kwargs):
    size = request.args.get('size')
    start = request.args.get('from')
    name = node_addon.system_user.username

    try:
        query = node_addon.routes[route]
    except KeyError:
        raise HTTPError(http.NOT_FOUND)

    q = node_addon.build_query(query, size, start)

    ret = search(q, _type=node_addon.namespace, index='metadata')

    rss_url = node_addon.owner.api_url_for('resolve_route_rss', _xml=True, _absolute=True, route=route)

    return elastic_to_rss(name, ret['results'], query, rss_url)


# POST
@must_have_permission('admin')
@must_have_addon('app', 'node')
def create_route(node_addon, **kwargs):
    route = request.json.get('route')
    query = request.json.get('query')
    exists = node_addon.routes.get(route) is not None

    if not route or not query or exists:
        raise HTTPError(http.BAD_REQUEST)

    node_addon.routes[route] = query
    node_addon.save()

    return {}, http.CREATED


# PUT
@must_have_permission('admin')
@must_have_addon('app', 'node')
def update_route(node_addon, route, **kwargs):
    query = request.json.get('query')

    if not query:
        raise HTTPError(http.BAD_REQUEST)

    if node_addon.routes.get(route):
        node_addon.routes[route] = query
        node_addon.save()
        return http.OK

    raise HTTPError(http.NOT_FOUND)


# DELETE
@must_have_permission('admin')
@must_have_addon('app', 'node')
def delete_route(node_addon, route, **kwargs):
    if not node_addon.routes.get(route):
        raise HTTPError(http.BAD_REQUEST)

    del node_addon.routes[route]
    node_addon.save()

    raise HTTPError(http.NO_CONTENT)
