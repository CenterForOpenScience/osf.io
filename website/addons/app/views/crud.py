import httplib as http

from flask import request

from framework.auth import Auth
from framework.exceptions import HTTPError

from website.search.search import search
from website.project import new_node
from website.project.decorators import (
    must_be_valid_project,
    must_have_addon, must_have_permission,
    must_not_be_registration, must_be_contributor_or_public
)


# GET
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def query_app(node_addon, **kwargs):
    q = request.args.get('q', '')
    ret = search(q, index='metadata')
    return {
        'results': [ blob['_source'] for blob in ret['hits']['hits']],
        'total': ret['hits']['total']
    }


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
    try:
        ret = search(node_addon[route], index='metadata')
        return {
            'results': ret['hits']['hits'],
            'total': ret['hits']['total']
        }
    except KeyError:
        raise HTTPError(http.NOT_FOUND)


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


# GET
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def get_metadata(node_addon, guid, **kwargs):
    try:
        return node_addon.get_data(guid)
    except TypeError:
        raise HTTPError(http.NOT_FOUND)


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


@must_have_permission('admin')
@must_have_addon('app', 'node')
def create_application_project(node_addon, **kwargs):
    if not request.json:
        raise HTTPError(http.BAD_REQUEST)

    try:
        assert len(request.json['title']) > 1 and len(request.json['title']) < 201
    except KeyError, AssertionError:
        raise HTTPError(http.BAD_REQUEST)

    node = new_node('project', request.json['title'], node_addon.system_user, request.json.get('description'))
    node.system_tags.append('application_created')
    node.set_privacy('public', auth=Auth(node_addon.system_user))

    return {
        'id': node._id,
        'url': node.url,
        'apiUlr': node.api_url
    }, http.CREATED
