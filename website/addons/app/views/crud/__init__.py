from __future__ import unicode_literals

import httplib as http

from flask import request

from modularodm.exceptions import ValidationError

from framework.auth import Auth
from framework.auth import User
from framework.flask import app
from framework.guid.model import Guid
from framework.exceptions import HTTPError

from website.project import Node
from website.project import new_node
from website.search.search import search
from website.project.decorators import must_have_addon
from website.search.exceptions import IndexNotFoundError
from website.search.exceptions import MalformedQueryError
from website.project.decorators import must_have_permission
from website.project.decorators import must_be_contributor_or_public

from website.addons.app.model import Metadata
from website.addons.app.utils import args_to_query
from website.addons.app.utils import elastic_to_rss
from website.addons.app.utils import elastic_to_atom
from website.addons.app.utils import elastic_to_changelist
from website.addons.app.utils import elastic_to_resourcelist
from website.addons.app.utils import generate_capabilitylist

from . import metadata, customroutes  # noqa


# GET
@must_have_permission('admin')
@must_have_addon('app', 'node')
def get_access(node_addon, **kwargs):
    key = request.get_json().get('key')

    if not key:
        raise HTTPError(http.BAD_REQUEST)

    node = node_addon.owner
    user = User.from_api_key(key)
    permissions = node.permissions.get(user._id)

    return {
        'permissions': permissions or []
    }


# GET
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def query_app(node_addon, **kwargs):
    q = request.args.get('q', '*')
    size = request.args.get('size')
    start = request.args.get('from')
    return_raw = request.args.get('raw') is not None

    query = args_to_query(q, size, start)

    try:
        ret = search(query, index='metadata', doc_type=node_addon.namespace, raw=True)
    except MalformedQueryError:
        raise HTTPError(http.BAD_REQUEST)
    except IndexNotFoundError:
        # TODO Deal with correct empty raw output
        return {
            'count': 0,
            'results': []
        }

    if return_raw:
        return ret

    return {
        'count': ret['hits']['total'],
        'results': [hit['_source'] for hit in ret['hits']['hits']]
    }

# POST
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def query_app_json(node_addon, **kwargs):
    if not request.json:
        raise HTTPError(http.BAD_REQUEST)

    return_raw = request.args.get('raw') is not None

    try:
        del request.json['format']
    except KeyError:
        pass

    query = request.json

    try:
        ret = search(query, index='metadata', doc_type=node_addon.namespace, raw=True)
    except MalformedQueryError:
        raise HTTPError(http.BAD_REQUEST)
    except IndexNotFoundError:
        # TODO Deal with correct empty raw output
        return {
            'count': 0,
            'results': []
        }

    if return_raw:
        return ret

    return {
        'count': ret['hits']['total'],
        'results': [hit['_source'] for hit in ret['hits']['hits']]
    }


# GET
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def query_app_rss(node_addon, **kwargs):
    q = request.args.get('q', '*')
    size = request.args.get('size')
    start = request.args.get('from')
    query = args_to_query(q, size, start)
    extended = request.args.get('extended')
    try:
        ret = search(query, doc_type=node_addon.namespace, index='metadata')
    except MalformedQueryError:
        raise HTTPError(http.BAD_REQUEST)
    except IndexNotFoundError:
        ret = {
            'count': 0,
            'results': []
        }

    node = node_addon.owner
    name = node_addon.system_user.username

    rss_url = node.api_url_for('query_app_rss', _xml=True, _absolute=True)
    if extended:
        return elastic_to_rss(name, ret['results'], q, rss_url, extended=True)
    else:
        return elastic_to_rss(name, ret['results'], q, rss_url)


# GET
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def query_app_atom(node_addon, **kwargs):
    q = request.args.get('q', '*')
    size = request.args.get('size')
    start = request.args.get('from')
    query = args_to_query(q, size, start)

    try:
        ret = search(query, doc_type=node_addon.namespace, index='metadata')
    except MalformedQueryError:
        raise HTTPError(http.BAD_REQUEST)
    except IndexNotFoundError:
        ret = {
            'count': 0,
            'results': []
        }

    node = node_addon.owner
    name = node_addon.system_user.username

    atom_url = node.api_url_for('query_app_atom', _xml=True, _absolute=True)
    return elastic_to_atom(name, ret['results'], q, atom_url)


# GET
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def query_app_resourcelist(node_addon, **kwargs):
    q = request.args.get('q', '*')
    size = request.args.get('size')
    start = request.args.get('from')
    name = node_addon.system_user.username

    q += ' NOT isResource:True'

    query = args_to_query(q, start, size)

    try:
        ret = search(query, doc_type=node_addon.namespace, index='metadata')
    except MalformedQueryError:
        raise HTTPError(http.BAD_REQUEST)
    except IndexNotFoundError:
        ret = {
            'count': 0,
            'results': []
        }

    return elastic_to_resourcelist(name, ret['results'], q)


@must_be_contributor_or_public
@must_have_addon('app', 'node')
def query_app_changelist(node_addon, **kwargs):
    q = request.args.get('q', '*')
    size = request.args.get('size')
    start = request.args.get('from')
    name = node_addon.system_user.username

    q += ' NOT isResource:True'

    query = args_to_query(q, start, size)

    try:
        ret = search(query, doc_type=node_addon.namespace, index='metadata')
    except MalformedQueryError:
        raise HTTPError(http.BAD_REQUEST)
    except IndexNotFoundError:
        ret = {
            'count': 0,
            'results': []
        }

    return elastic_to_changelist(name, ret['results'], q)


@must_be_contributor_or_public
@must_have_addon('app', 'node')
def query_app_capabilitylist(node_addon, **kwargs):
    node = node_addon.owner
    resourcelist_url = node.api_url_for('query_app_resourcelist', _xml=True, _absolute=True)
    changelist_url = node.api_url_for('query_app_changelist', _xml=True, _absolute=True)

    return generate_capabilitylist(resourcelist_url, changelist_url)


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

    if _metadata:
        _metadata['attached'] = {
            'nid': node._id,
            'pid': node.parent_id
        }
        metastore = Metadata(app=node_addon, data=_metadata)
        metastore.save()

    return {
        'id': node._id,
        'mid': metastore._id,
        'url': node.url,
        'apiUrl': node.api_url
    }, http.CREATED


@must_be_contributor_or_public
@must_have_addon('app', 'node')
def get_project_metadata(node_addon, guid, **kwargs):
    node = Node.load(guid)
    if not node:
        raise HTTPError(http.NOT_FOUND)

    sort_on = request.args.get('sort')

    query = {
        'query': {
            'filtered': {
                'filter': {
                    'term': {
                        'nid': node._id
                    }
                }
            }
        }
    }

    try:
        rets = search(query, doc_type=node_addon.namespace, index='metadata')
    except IndexNotFoundError:
        return {}

    ret = {}
    for blob in reversed(sorted(rets['results'], key=lambda x: x.get(sort_on))):
        ret.update(blob)

    return ret


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
