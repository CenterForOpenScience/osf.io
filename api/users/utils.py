from modularodm import Q
from rest_framework.exceptions import NotFound
from website.project import Node

__author__ = 'patrickgorman'


class IncludeAdditionalQuery(object):

    def __init__(self, obj, request):
        self.obj = obj
        self.request = request

    def get_additional_query(self):
        query = {}
        if 'include' in self.request.query_params:
            params = self.request.query_params['include'].split(',')
            if 'nodes' in params:
                query['nodes'] = self.get_nodes()
                params.remove('nodes')
            if params != []:
                params_string = ', '.join(params)
                raise NotFound('The following arguments cannot be found: {}'.format(params_string))
        return query

    def get_nodes(self):
        nodes = {}
        # todo Edit to hide private projects without current user view permissions
        query = (
            Q('contributors', 'eq', self.obj) &
            Q('is_folder', 'ne', True) &
            Q('is_deleted', 'ne', True)
        )
        node_list = Node.find(query)
        # todo make simple serializer for nodes
        for node in node_list:
            nodes[node._id] = {
                'title': node.title,
                'description': node.description,
                'is_public': node.is_public
            }
        return nodes
