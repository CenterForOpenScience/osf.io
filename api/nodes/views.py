import requests

from rest_framework import generics, permissions as drf_permissions
from modularodm import Q

from website.models import Node
from api.base.utils import get_object_or_404, waterbutler_url_for
from api.base.filters import ODMFilterMixin
from .serializers import NodeSerializer, NodePointersSerializer, NodeFilesSerializer
from api.users.serializers import UserSerializer
from .permissions import ContributorOrPublic, ReadOnlyIfRegistration


class NodeMixin(object):
    """Mixin with convenience methods for retrieving the current node based on the
    current URL. By default, fetches the current node based on the pk kwarg.
    """

    serializer_class = NodeSerializer
    node_lookup_url_kwarg = 'pk'

    def get_node(self):
        obj = get_object_or_404(Node, self.kwargs[self.node_lookup_url_kwarg])
        # May raise a permission denied
        self.check_object_permissions(self.request, obj)
        return obj


class NodeList(generics.ListCreateAPIView, ODMFilterMixin):
    """Return a list of nodes. By default, a GET
    will return a list of public nodes, sorted by date_modified.
    """
    # TODO: Allow unauthenticated requests (list public projects, e.g.)
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
    )
    serializer_class = NodeSerializer
    ordering = ('-date_modified', )  # default ordering

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        return (
            Q('is_deleted', 'ne', True) &
            Q('is_folder', 'ne', True)
        )

    # overrides ListCreateAPIView
    def get_queryset(self):
        query = self.get_query_from_request()
        return Node.find(query)

    # overrides ListCreateAPIView
    def perform_create(self, serializer):
        # On creation, make sure that current user is the creator
        user = self.request.user
        serializer.save(creator=user)


class NodeDetail(generics.RetrieveUpdateAPIView, NodeMixin):

    permission_classes = (
        ContributorOrPublic,
        ReadOnlyIfRegistration,
    )
    serializer_class = NodeSerializer

    # overrides RetrieveUpdateAPIView
    def get_object(self):
        return self.get_node()

    # overrides RetrieveUpdateAPIView
    def get_serializer_context(self):
        # Serializer needs the request in order to make an update to privacy
        return {'request': self.request}


class NodeContributorsList(generics.ListAPIView, NodeMixin):
    """Return the contributors (users) fora node."""

    permission_classes = (
        ContributorOrPublic,
    )

    serializer_class = UserSerializer

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_node().visible_contributors


class NodeRegistrationsList(generics.ListAPIView, NodeMixin):
    permissions_classes = (
        ContributorOrPublic,
    )
    serializer_class = NodeSerializer

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_node().node__registrations


class NodeChildrenList(generics.ListAPIView, NodeMixin):
    serializer_class = NodeSerializer

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_node().nodes


class NodePointersList(generics.ListAPIView, NodeMixin):
    serializer_class = NodePointersSerializer

    def get_queryset(self):
        return self.get_node().nodes_pointer


class NodeFilesList(generics.ListAPIView, NodeMixin):
    serializer_class = NodeFilesSerializer

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
    )

    def get_valid_self_link_methods(self, user, root_folder=False):
        valid_methods = {
                'file': [],
                'folder': [],
            }
        if user is None:
            return valid_methods

        permissions = self.get_node().get_permissions(user)
        if 'read' in permissions:
            valid_methods['file'].append('GET')
        if 'write' in permissions:
            valid_methods['file'].append('POST')
            valid_methods['file'].append('DELETE')
            valid_methods['folder'].append('POST')
            if not root_folder:
                valid_methods['folder'].append('DELETE')

        return valid_methods

    def get_file_item(self, item, valid_file_methods, node_id, cookie, obj_args):
        file= {
                    'valid_self_link_methods': valid_file_methods[item['kind']],
                    'provider': item['provider'],
                    'path': item['path'],
                    'name': item['name'],
                    'node_id': node_id,
                    'cookie': cookie,
                    'args': obj_args,
                    'waterbutler_type': 'file',
                    'item_type': item['kind'],
                }
        if file['item_type'] == 'folder':
            file['metadata'] = {}
        else:
            file['metadata'] = {
                'content_type': item['contentType'],
                'modified': item['modified'],
                'size': item['size'],
                'extra': item['extra'],
            }
        return file

    def get_queryset(self):
        query_params = self.request.query_params

        addons = self.get_node().get_addons()
        user = self.request.user
        cookie = user.get_or_create_cookie() if self.request.user else None
        node_id = self.get_node()._id
        obj_args = self.request.parser_context['args']

        provider = query_params['provider'] if 'provider' in query_params else None
        path = query_params['path'] if 'path' in query_params else '/'
        files = []

        if provider is None:
            valid_self_link_methods = self.get_valid_self_link_methods(user, True)
            for addon in addons:
                if addon.config.has_hgrid_files:
                    files.append({
                        'valid_self_link_methods': valid_self_link_methods,
                        'provider': addon.config.short_name,
                        'name': addon.config.short_name,
                        'path': path,
                        'node_id': node_id,
                        'cookie': cookie,
                        'args': obj_args,
                        'waterbutler_type': 'data',
                        'item_type': 'folder',
                        'metadata': {},
                    })
        else:
            valid_self_link_methods = self.get_valid_self_link_methods(user, False)
            url = waterbutler_url_for('data', provider, path, self.kwargs['pk'], node_id, obj_args)
            waterbutler_request = requests.get(url)
            waterbutler_data = waterbutler_request.json()['data']
            if isinstance(waterbutler_data, list):
                for item in waterbutler_data:
                    file = self.get_file_item(item, valid_self_link_methods, node_id, cookie, obj_args)
                    files.append(file)
            else:
                files.append(self.get_file_item(waterbutler_data, valid_self_link_methods, node_id, cookie, obj_args))

        return files

    def get_current_user(self):
        request = self.context['request']
        user = request.user
        return user
