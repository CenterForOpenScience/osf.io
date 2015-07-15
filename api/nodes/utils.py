from rest_framework.exceptions import NotFound
from framework.auth.core import Auth


class IncludeAdditionalQueryNode(object):

    def __init__(self, obj, request):
        self.obj = obj
        self.request = request

    def get_additional_query(self):
        query = {}
        if 'include' in self.request.query_params:
            params = self.request.query_params['include'].split(',')
            if 'children' in params:
                query['children'] = self.get_children()
                params.remove('children')
            if 'contributors' in params:
                query['contributors'] = self.get_contributors()
                params.remove('contributors')
            if 'files' in params:
                query['files'] = self.get_files()
                params.remove('files')
            if 'pointers' in params:
                query['pointers'] = self.get_pointers()
                params.remove('pointers')
            if 'registrations' in params:
                query['registrations'] = self.get_registrations()
                params.remove('registrations')
            if params != []:
                params_string = ', '.join(params)
                raise NotFound('The following arguments cannot be found: {}'.format(params_string))
        return query

    # todo make simple serializer for children
    def get_children(self):
        nodes = {}
        for node in self.obj.nodes:
            if node.can_view(Auth(self.request.user)) and node.primary:
                nodes[node._id] = {
                    'title': node.title,
                    'description': node.description,
                    'is_public': node.is_public
                }
        return nodes

    # todo make simple serializer for contributors
    def get_contributors(self):
        contributors = {}
        for contributor in self.obj.contributors:
            contributors[contributor._id] = {
                'username': contributor.username,
                'bibliographic': self.obj.get_visible(contributor),
                'permissions': self.obj.get_permissions(contributor)
            }
        return contributors

    # todo figure out how to get file data from providers
    def get_files(self):
        files = {'test': 'not yet functional'}
        # for files in self.obj.files:
        #     files[file.name] = {
        #         'provider': file.proivider,
        #         'size': file.size,
        #     }
        return files

    # todo make simple serializer for pointers
    def get_pointers(self):
        pointers = {}
        for pointer in self.obj.nodes_pointer:
            pointers[pointer._id] = {
                'title': pointer.title,
                'description': pointer.description,
                'is_public': pointer.is_public
            }
        return pointers

    def get_registrations(self):
        registrations = {}
        for registration in self.obj.node__registrations:
            registrations[registration._id] = {
                'title': registration.title,
                'description': registration.description,
                'is_public': registration.is_public
            }
        return registrations
