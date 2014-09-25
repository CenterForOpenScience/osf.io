# -*- coding: utf-8 -*-
"""Utility functions for the Application add-on.
"""
from __future__ import unicode_literals

from modularodm.exceptions import ValidationError

from framework.auth import Auth
from framework.guid.model import Metadata, Guid

from website.project import new_node, Node
from website.search import search

def find_or_create_from_report(report, app):
    # @chrisseto TODO: Find a better way to do this
    # The parent projects need to be marked, currently
    # this could be overwritten
    search_string = 'is_project:true;doi:"{doc[id][doi]}";title:"{doc[title]}"'
    search_string = search_string.format(doc=report)

    try:
        ret = search.search(search_string, _type=app.namespace, index='metadata')
    except Exception:
        ret = None

    if ret and ret['hits']['total'] > 0:
        if ret['hits']['hits'][0]['_source']['title'] == report['title']:
            return Node.load(ret['hits']['hits'][0]['_source']['guid'])

    resource = new_node('project', report['title'], app.system_user, description=report.get('description'))
    resource.set_privacy('public')
    resource.save()
    # TODO Discuss the below
    app.attach_system_data(resource._id, {'is_project': 'true'})
    return resource


def find_or_create_report(node, report, node_addon, metadata=None):
    for child in node.nodes:
        provider = child.title.split(' :')[0]
        if provider == report['source']:
            return child

    report_node = new_node('report', '{}: {}'.format(report['source'], report['title']), node_addon.system_user,
            description=report.get('description'), project=node)

    report_node.set_privacy('public')

    for contributor in report['contributors']:
        try:
            report_node.add_unregistered_contributor(contributor['full_name'],
                    contributor.get('email'), Auth(node_addon.system_user),
                    permissions=['read'])
        except ValidationError:
            pass  # A contributor with the given email has already been added

    for tag in report['tags']:
        report_node.add_tag(tag, Auth(node_addon.system_user))

    report_node.save()

    if not metadata:
        node_addon.attach_data(report_node._id, report)
    else:
        metadata.guid = report_node._id
        metadata.save()

        guid = Guid.load(report_node._id)
        guid.metastore[node_addon.namespace] = metadata._id
        guid.save()

    return report_node


def create_orphaned_metadata(node_addon, report):
    metastore = Metadata(app=node_addon)
    metastore.update(report)
    metastore.system_data['is_orphan'] = True
    metastore.system_data['guid'] = metastore._id
    metastore.save()

    search.update_metadata(metastore)

    return metastore


def is_claimed(node):
    for contributor in node.contributors:
        if contributor.is_claimed and not contributor.is_system_user:
            return True
    return False
