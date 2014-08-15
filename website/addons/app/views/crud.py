import httplib as http

from flask import request

from framework.exceptions import HTTPError

from website.search import search

from website.project.decorators import (
    must_be_valid_project,
    must_have_addon, must_have_permission,
    must_not_be_registration, must_be_contributor_or_public
)


# GET
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def query_app(node_addon, **kwargs):
    pass


# GET
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def resolve_route(node_addon, route, **kwargs):
    try:
        return {'results': search(node_addon[route], index='metadata')}
    except KeyError:
        raise HTTPError(http.NOT_FOUND)


# POST
@must_have_permission('admin')
@must_have_addon('app', 'node')
def create_route(node_addon, **kwargs):
    import ipdb; ipdb.set_trace()
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


# GET
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def get_metadata(node_addon, guid, **kwargs):
    return node_addon.get_data(guid)


# POST, PUT
@must_have_permission('write')
@must_have_addon('app', 'node')
def add_metadata(node_addon, guid, **kwargs):
    metadata = request.json

    if not metadata:
        raise HTTPError(http.BAD_REQUEST)
    try:
        node_addon.attach_data(guid, metadata)
        node_addon.save()
    except TypeError:
        raise HTTPError(http.BAD_REQUEST)


# DELETE
@must_have_permission('admin')
@must_have_addon('app', 'node')
def delete_metadata(node_addon, guid, **kwargs):
    key = request.args.get('key')

    try:
        node_addon.delete_data(guid, key=key)
    except KeyError:
        raise HTTPError(http.BAD_REQUEST)

    if key:
        return {
            'deleted': key
        }, http.OK

    return HTTPError(http.NO_CONTENT)
