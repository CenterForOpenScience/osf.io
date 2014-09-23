from __future__ import unicode_literals

import httplib as http

from flask import request

from modularodm.exceptions import ValidationError

from framework.auth import Auth
from framework.flask import app
from framework.exceptions import HTTPError
from framework.guid.model import Guid

from website.search.search import search
from website.project import new_node
from website.project.decorators import (
    must_be_valid_project,
    must_have_addon, must_have_permission,
    must_not_be_registration, must_be_contributor_or_public
)

from website.addons.app.utils import find_or_create_from_report, is_claimed

from . import metadata, customroutes


# GET
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def query_app(node_addon, **kwargs):
    q = request.args.get('q', '')
    start = request.args.get('page', 0)

    ret = search(q, _type=node_addon.namespace, index='metadata', start=start)
    return {
        'results': [blob['_source'] for blob in ret['hits']['hits']],
        'total': ret['hits']['total']
    }


@must_have_permission('admin')
@must_have_addon('app', 'node')
def create_application_project(node_addon, **kwargs):
    if not request.json:
        raise HTTPError(http.BAD_REQUEST)

    try:
        assert len(request.json['title']) > 1 and len(request.json['title']) < 201
    except (KeyError, AssertionError):
        raise HTTPError(http.BAD_REQUEST)

    node = new_node('project', request.json['title'], node_addon.system_user, request.json.get('description'))
    node.set_privacy('public', auth=Auth(node_addon.system_user))

    return {
        'id': node._id,
        'url': node.url,
        'apiUrl': node.api_url
    }, http.CREATED


@must_have_permission('admin')
@must_have_addon('app', 'node')
def create_report(node_addon, **kwargs):
    report = request.json

    try:
        resource = find_or_create_from_report(report, node_addon)
    except KeyError:
        raise HTTPError(http.BAD_REQUEST)

    # This may not be the best behavior
    # This will just merge the documents in a not super smart way
    # Keys and nested key will be updated and empty fields filled in
    node_addon.attach_data(resource._id, report)

    claimed = is_claimed(resource)

    report_node = new_node('report', '{}: {}'.format(report['source'], report['title']), node_addon.system_user,
            description=report.get('description'), project=resource)

    report_node.set_privacy('public')

    for contributor in report['contributors']:
        if not claimed:
            try:
                resource.add_unregistered_contributor(contributor['full_name'],
                        contributor.get('email'), Auth(node_addon.system_user),
                        permissions=['admin'])  # TODO Discuss this
            except ValidationError:
                pass  # A contributor with the given email has already been added

        try:
            report_node.add_unregistered_contributor(contributor['full_name'],
                    contributor.get('email'), Auth(node_addon.system_user),
                    permissions=['read'])
        except ValidationError:
            pass  # A contributor with the given email has already been added

    report_node.save()

    for tag in report['tags']:
        report_node.add_tag(tag, Auth(node_addon.system_user))
        if not claimed:
            resource.add_tag(tag, Auth(node_addon.system_user))

    node_addon.attach_data(report_node._id, report)

    return {
        'id': report_node._id,
        'url': report_node.url,
        'apiUrl': report_node.api_url,
        'resource': {
            'id': resource._id,
            'url': resource.url,
            'apiUrl': resource.api_url
        }
    }, http.CREATED


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
