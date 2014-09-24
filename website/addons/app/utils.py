# -*- coding: utf-8 -*-
"""Utility functions for the Application add-on.
"""
from __future__ import unicode_literals

from website.project import new_node, Node
from website.search.search import search

def find_or_create_from_report(report, app):
    # @chrisseto TODO: Find a better way to do this
    # The parent projects need to be marked, currently
    # this could be overwritten
    search_string = 'is_project:true;doi:"{doc[id][doi]}";title:"{doc[title]}"'
    search_string = search_string.format(doc=report)

    try:
        ret = search(search_string, _type=app.namespace, index='metadata')
    except Exception:
        ret = None

    if ret and ret['hits']['total'] > 0:
        if ret['hits']['hits'][0]['_source']['title'] == report['title']:
            return Node.load(ret['hits']['hits'][0]['_source']['guid'])

    resource = new_node('project', report['title'], app.system_user, description=report.get('description'))
    resource.set_privacy('public')
    resource.save()
    # TODO Address this issue
    app.attach_data(resource._id, {'is_project': 'true'})
    return resource


def is_claimed(node):
    for contributor in node.contributors:
        if contributor.is_claimed and not contributor.is_system_user:
            return True
    return False
