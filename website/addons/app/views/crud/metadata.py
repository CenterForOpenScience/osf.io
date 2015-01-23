from __future__ import unicode_literals

import httplib as http

from flask import request

from modularodm.exceptions import ValidationError

from framework.auth import Auth
from framework.exceptions import HTTPError

from website.project import new_node, Node
from website.addons.app.types import TYPE_MAP
from website.addons.app.model import Metadata
from website.project.decorators import must_have_addon
from website.search.exceptions import TypeCollisionError
from website.project.decorators import must_have_permission
from website.addons.app.exceptions import InvalidSchemaError
from website.addons.app.exceptions import SchemaViolationError
from website.project.decorators import must_be_contributor_or_public


@must_be_contributor_or_public
@must_have_addon('app', 'node')
def get_schema_types(node_addon, **kwargs):
    return {
        key: value.__doc__
        for key, value
        in TYPE_MAP.items()
    }


@must_be_contributor_or_public
@must_have_addon('app', 'node')
def get_schema(node_addon, **kwargs):
    return node_addon._schema


@must_have_permission('admin')
@must_have_addon('app', 'node')
def post_schema(node_addon, **kwargs):
    if not request.json:
        raise HTTPError(http.BAD_REQUEST)

    try:
        node_addon.schema = request.json.copy()
    except InvalidSchemaError as e:
        raise HTTPError(http.BAD_REQUEST, data={'reason': e.message})

    node_addon.strict = bool(request.args.get('strict'))

    node_addon.save()
    return {}, http.CREATED


@must_have_permission('admin')
@must_have_addon('app', 'node')
def delete_schema(node_addon, **kwargs):
    node_addon.schema = {}
    node_addon.save()
    return {}, http.NO_CONTENT


@must_be_contributor_or_public
@must_have_addon('app', 'node')
def get_metadata_ids(node_addon, **kwargs):
    return {
        'ids': [m._id for m in node_addon.metadata__owner]
    }


# GET
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def get_metadata(node_addon, mid, **kwargs):
    meta = Metadata.load(mid)

    if not meta:
        raise HTTPError(http.NOT_FOUND)

    if meta.namespace != node_addon.namespace:
        raise HTTPError(http.FORBIDDEN)

    return meta.to_json()


# POST
@must_have_permission('write')
@must_have_addon('app', 'node')
def create_metadata(node_addon, **kwargs):
    metadata = request.json

    if not metadata:
        raise HTTPError(http.BAD_REQUEST)

    metastore = Metadata(app=node_addon, data=metadata)

    try:
        metastore.save()
    except SchemaViolationError as e:
        raise HTTPError(http.BAD_REQUEST, data={'reason': e.message})

    return {
        'id': metastore._id
    }, http.CREATED


# PUT
@must_have_permission('write')
@must_have_addon('app', 'node')
def update_metadata(node_addon, mid, **kwargs):
    metadata = request.json

    if not metadata:
        raise HTTPError(http.BAD_REQUEST)

    metastore = Metadata.load(mid)

    if not metastore:
        raise HTTPError(http.NOT_FOUND)

    if metastore.namespace != node_addon.namespace:
        raise HTTPError(http.FORBIDDEN)

    metastore.update(metadata)

    try:
        metastore.save()
    except SchemaViolationError as e:
        raise HTTPError(http.BAD_REQUEST, data={'reason': e.message})
    except TypeCollisionError:
        raise HTTPError(http.BAD_REQUEST)


# DELETE
@must_have_permission('admin')
@must_have_addon('app', 'node')
def delete_metadata(node_addon, mid, **kwargs):
    metastore = Metadata.load(mid)

    if not metastore:
        return HTTPError(http.NOT_FOUND)

    if metastore.namespace != node_addon.namespace:
        raise HTTPError(http.FORBIDDEN)

    key = request.args.get('key', None)

    if key:
        for k in key.split(','):
            try:
                del metastore[k]
            except KeyError:
                pass

        metastore.save()

        return {
            'deleted': key
        }, http.OK

    Metadata.remove_one(metastore, True)

    raise HTTPError(http.NO_CONTENT)


# @must_have_permission('write')
@must_have_addon('app', 'node')
def promote_metadata(node_addon, mid, **kwargs):
    metastore = Metadata.load(mid)
    request_json = request.json or {}

    if not metastore:
        raise HTTPError(http.NOT_FOUND)

    if metastore.namespace != node_addon.namespace:
        raise HTTPError(http.FORBIDDEN)

    node = metastore.parent or metastore.node

    if node:
        return {
            'id': node._id,
            'url': node.url,
            'apiUrl': node.api_url
        }

    creator = node_addon.system_user
    tags = request_json.get('tags') or metastore.get('tags', [])
    contributors = request_json.get('contributors') or metastore.get('contributors', [])
    for contributor in contributors:
        contributor['full_name'] = ' '.join([
            contributor['given'],
            contributor['middle'],
            contributor['family']
        ]).strip()
    category = request_json.get('category') or metastore.get('category', 'project')
    title = request_json.get('title') or metastore.get('title', 'No Title')
    project = Node.load(request_json.get('parent') or metastore.get('parent'))
    description = request_json.get('description') or metastore.get('description')

    node = new_node(category, title, creator, description, project)

    node.set_privacy('public')

    for tag in tags:
        node.add_tag(tag, Auth(creator))

    for contributor in contributors:
        try:
            node.add_unregistered_contributor(contributor['full_name'],
                contributor.get('email'), Auth(creator))
        except ValidationError:
            pass  # A contributor with the given email has already been added
    node.save()

    metastore['attached'] = {
        'nid': node._id,
        'pid': node.parent_id
    }
    metastore.save()

    return {
        'id': node._id,
        'url': node.url,
        'apiUrl': node.api_url
    }, http.CREATED
