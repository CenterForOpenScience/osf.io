# -*- coding: utf-8 -*-
"""Utility functions for the Application add-on.
"""
from website.project import new_node, Node
from website.search.search import search

def find_or_create_from_report(report, app):
    search_map = {
        'doi': ['id', 'doi'],
        'title': ['title']
    }
    # @chrisseto TODO: Find a better way to do this
    # The parent projects need to be marked, currently
    # this could be overwritten
    search_string = 'is_project:true;'

    for key, val in search_map.items():
        tmp = report
        for _key in val:
            tmp = tmp[_key]

        search_string += '{}:{};'.format(key, tmp)

        ret = search(search_string, _type=app.namespace, index='metadata')

        if not ret:
            break

        if ret['hits']['total'] == 1:
            return Node.load(ret['hits']['hits'][0]['_source']['guid'])
        elif ret['hits']['total'] == 0:
            break

    resource = new_node('project', report['title'], app.system_user, description=report.get('description'))
    resource.set_privacy('public')
    # resource.set_visible(app.system_user, False, log=False)
    resource.save()
    # TODO Address this issue
    app.attach_data(resource._id, {'is_project': 'true'})
    return resource


def is_claimed(node):
    for contributor in node.contributors:
        if contributor.is_claimed and not contributor.is_system_user:
            return True
    return False
