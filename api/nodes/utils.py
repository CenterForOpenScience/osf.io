from rest_framework.exceptions import NotFound
from framework.auth.core import Auth
from api.base.utils import waterbutler_url_for
from rest_framework.exceptions import PermissionDenied, ValidationError


class IncludeAdditionalQueryNode(object):

    def __init__(self, node, request):
        self.node = node
        self.request = request

    # todo: make simple serializers for parameters?
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

    def get_children(self):
        nodes = {}
        for node in self.node.nodes:
            if (node.can_view(Auth(self.request.user)) or node.is_public) and node.primary:
                nodes[node._id] = {
                    'title': node.title,
                    'description': node.description,
                    'is_public': node.is_public,
                }
        return nodes

    def get_contributors(self):
        contributors = {}
        for contributor in self.node.contributors:
            contributors[contributor._id] = {
                'username': contributor.username,
                'bibliographic': self.node.get_visible(contributor),
                'permissions': self.node.get_permissions(contributor)
            }
        return contributors

    # todo edit once files are easier to locate
    def get_files(self):
        files = {}
        for file in self.get_file_list():
            files[file['name']] = {
                'provider': file['provider'],
                'path': file['path'],
                'args': file['args'],
            }
        return files

    def get_pointers(self):
        pointers = {}
        for pointer in self.node.nodes_pointer:
            pointers[pointer._id] = {
                'title': pointer.title,
                'description': pointer.description,
                'is_public': pointer.is_public
            }
        return pointers

    def get_registrations(self):
        registrations = {}
        for registration in self.node.node__registrations:
            if registration.can_view(Auth(self.request.user)) or registration.is_public:
                registrations[registration._id] = {
                    'title': registration.title,
                    'description': registration.description,
                    'is_public': registration.is_public
                }
        return registrations

    # todo configure this after issue 3060 is resolved
    # copied and slightly altered from views
    def get_file_list(self):
        query_params = self.request.query_params

        addons = self.node.get_addons()
        user = self.request.user
        node_args = self.request.parser_context['args']

        provider = query_params.get('provider')
        path = query_params.get('path', '/')
        files = []

        if provider is None:
            for addon in addons:
                if addon.config.has_hgrid_files:
                    files.append({
                        'provider': addon.config.short_name,
                        'name': addon.config.short_name,
                        'path': path,
                        'args': node_args,
                    })
        else:
            cookie = None if self.request.user.is_anonymous() else user.get_or_create_cookie()
            url = waterbutler_url_for('data', provider, path, self.kwargs['node_id'], cookie, node_args)
            waterbutler_request = self.request.get(url)
            if waterbutler_request.status_code == 401:
                raise PermissionDenied
            try:
                waterbutler_data = waterbutler_request.json()['data']
            except KeyError:
                raise ValidationError(detail='detail: Could not retrieve files information.')

            if isinstance(waterbutler_data, list):
                for item in waterbutler_data:
                    file = self.get_file_item(item, node_args)
                    files.append(file)
            else:
                files.append(self.get_file_item(waterbutler_data, node_args))

        return files

    def get_file_item(self, item, node_args):
        file_item = {
            'provider': item['provider'],
            'path': item['path'],
            'name': item['name'],
            'args': node_args,
        }
        if file_item['item_type'] == 'folder':
            file_item['metadata'] = {}
        else:
            file_item['metadata'] = {
                'content_type': item['contentType'],
                'modified': item['modified'],
                'size': item['size'],
                'extra': item['extra'],
            }
        return file_item
