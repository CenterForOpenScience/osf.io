import httplib as http

from flask import redirect, request

from framework.exceptions import HTTPError

from website.project.decorators import (must_be_valid_project,
    must_have_addon, must_have_permission, must_not_be_registration
)


# GET
@must_have_permission('admin')
@must_have_addon('app', 'node')
def resolve_route(node_addon, route, **kwargs):
    try:
        return redirect(node_addon.resolve_route(route))
    except KeyError:
        raise HTTPError(http.NOT_FOUND)


# POST, PUT
@must_have_permission('admin')
@must_have_addon('app', 'node')
def create_route(node_addon, **kwargs):
    route = request.json.get('route') or kwargs.get('route')
    reroute = request.json.get('reroute')

    if not route or reroute:
        raise HTTPError(http.BAD_REQUEST)

    created = not node_addon.custom_routes.get(route)
    node_addon.add_custom_route(route, reroute)

    if created:
        return http.CREATED


# DELETE
@must_have_permission('admin')
@must_have_addon('app', 'node')
def delete_route(node_addon, route):
    if not node_addon.custom_routes.get(route):
        raise HTTPError(http.BAD_REQUEST)

    del node_addon.custom_routes[route]
    node_addon.save()

    return http.NO_CONTENT


@must_have_permission('read')
@must_have_addon('app', 'node')
def get_metadata(node_addon, guid, **kwargs):
    return node_addon.get_metadata(guid)


@must_have_permission('write')
@must_have_addon('app', 'node')
def add_metadata(node_addon, guid, **kwargs):
    metadata = request.json.get('metadata')

    if not metadata:
        raise HTTPError(http.BAD_REQUEST)

    node_addon.attach_data(guid, metadata)
    node_addon.save()
