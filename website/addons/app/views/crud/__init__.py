from __future__ import unicode_literals

import httplib as http

from flask import request

from modularodm.exceptions import ValidationError

from framework.auth import Auth
from framework.flask import app
from framework.exceptions import HTTPError
from framework.guid.model import Guid

from website.search.search import search
from website.project import new_node, Node
from website.project.decorators import (
    must_be_valid_project,
    must_have_addon, must_have_permission,
    must_not_be_registration, must_be_contributor_or_public
)

from website.addons.app.utils import elastic_to_rss

from . import metadata, customroutes


# GET
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def query_app(node_addon, **kwargs):
    q = request.args.get('q', '')
    start = request.args.get('page', 0)

    try:
        ret = search(q, _type=node_addon.namespace, index='metadata', start=start)
    except Exception:
        # TODO Fix me
        return {
            'results': [],
            'total': 0
        }

    return {
        'results': [blob['_source'] for blob in ret['hits']['hits']],
        'total': ret['hits']['total']
    }


# GET
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def query_app_rss(node_addon, **kwargs):
    q = request.args.get('q', '*')
    start = request.args.get('page', 0)
    name = node_addon.system_user.username
    ret = search(q, _type=node_addon.namespace, index='metadata', start=start, size=100)

    return elastic_to_rss(name, [blob['_source'] for blob in ret['hits']['hits']], q)


@must_have_permission('admin')
@must_have_addon('app', 'node')
def create_application_project(node_addon, **kwargs):
    if not request.json:
        raise HTTPError(http.BAD_REQUEST)

    try:
        assert len(request.json['title']) > 1 and len(request.json['title']) < 201
    except (KeyError, AssertionError):
        raise HTTPError(http.BAD_REQUEST)

    auth = Auth(node_addon.system_user)

    tags = request.json.get('tags', [])
    _metadata = request.json.get('metadata')
    parent = Node.load(request.json.get('parent'))
    privacy = request.json.get('privacy', 'public')
    category = request.json.get('category', 'project')
    contributors = request.json.get('contributors', [])
    system_metadata = request.json.get('systemData', {})
    permissions = request.json.get('permissions', ['admin'])

    node = new_node(category, request.json['title'], node_addon.system_user, request.json.get('description'), project=parent)

    for tag in tags:
        node.add_tag(tag, auth)

    for contributor in contributors:
        try:
            node.add_unregistered_contributor(contributor['name'],
                contributor.get('email'), auth,
                permissions=permissions)
        except ValidationError:
            pass  # A contributor with the given email has already been added

    node.set_privacy(privacy, auth=auth)

    node_addon.attach_data(node._id, _metadata)
    node_addon.attach_system_data(node._id, system_metadata)

    return {
        'id': node._id,
        'url': node.url,
        'apiUrl': node.api_url
    }, http.CREATED


@must_have_permission('admin')
@must_have_addon('app', 'node')
def update_application_project(node_addon, guid, **kwargs):
    node = Node.load(guid)

    if not request.json or not node:
        raise HTTPError(http.BAD_REQUEST)

    if request.json.get('title'):
        title_len = len(request.json['title'])
        if title_len < 0 or title_len > 201:
            raise HTTPError(http.BAD_REQUEST)
        node.title = request.json['title']

    if request.json.get('description'):
        node.description = request.json['description']

    auth = Auth(node_addon.system_user)

    tags = request.json.get('tags', [])

    for tag in tags:
        node.add_tag(tag, auth)

    contributors = request.json.get('contributors')
    permissions = request.json.get('permissions', ['admin'])

    if contributors:
        for contrib in node.contributors:
            if contrib.fullname not in contributors and not contrib.is_system_user:
                node.remove_contributor(contrib, auth)

        names = [x.fullname for x in node.contributors]

        for contributor in contributors:
            if contributor['name'] not in names:
                try:
                    node.add_unregistered_contributor(contributor['name'],
                        contributor.get('email'), auth,
                        permissions=permissions)
                except ValidationError:
                    pass  # A contributor with the given email has already been added

    node.save()

    return http.OK


@must_have_permission('write')
@must_have_addon('app', 'node')
def act_as_application(node_addon, route, **kwargs):
    route = route.split('/')

    try:
        route[0] = Guid.load(route[0]).referent.deep_url[1:-1]
    except AttributeError:
        pass

    proxied_action = '/api/v1/{}/'.format('/'.join(route))

    match = app.url_map.bind('').match(proxied_action, method=request.method)

    if match[0] == 'JSONRenderer__resolve_guid':
        raise HTTPError(http.NOT_FOUND)

    match[1].update({
        'auth': Auth(node_addon.system_user)
    })
    return app.view_functions[match[0]](**match[1])
