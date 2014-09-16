from __future__ import unicode_literals

import httplib as http

from flask import request, redirect

from framework.auth import Auth
from framework.exceptions import HTTPError

from website.search.search import search
from website.project import new_node, Node
from website.project.decorators import (
    must_be_valid_project,
    must_have_addon, must_have_permission,
    must_not_be_registration, must_be_contributor_or_public
)

from website.addons.app.utils import find_or_create_from_report

from . import metadata, customroutes


# GET
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def query_app(node_addon, **kwargs):
    q = request.args.get('q', '')
    start = request.args.get('page', 0)

    ret = search(q, _type=node_addon.namespace, index='metadata', start=start)
    return {
        'results': [ blob['_source'] for blob in ret['hits']['hits']],
        'total': ret['hits']['total']
    }


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

    for contributor in report['contributors']:
        resource.add_unregistered_contributor(contributor['full_name'], contributor.get('email'), Auth(node_addon.system_user))

    # This may not be the best behavior
    # This will just merge the documents in a not super smart way
    # Keys and nested key will be updated and empty fields filled in
    node_addon.attach_data(resource._id, report)

    report_node = new_node('report', '{}: {}'.format(report['source'], report['title']), node_addon.system_user,
            description=report.get('description'), project=resource)

    report_node.set_privacy('public')
    report_node.save()

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
def act_as_application(node_addon, tid, **kwargs):
    target_node = Node.load(tid)
