import requests

from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from modularodm import Q

from framework.auth.core import Auth
from website.models import Node, Pointer
from api.base.utils import get_object_or_404, waterbutler_url_for
from api.base.filters import ODMFilterMixin, ListFilterMixin
from .serializers import NodeSerializer, NodePointersSerializer, NodeFilesSerializer
from api.users.serializers import ContributorSerializer
from .permissions import ContributorOrPublic, ReadOnlyIfRegistration, ContributorOrPublicForPointers


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
    """Projects and components.

    On the front end, nodes are considered 'projects' or 'components'. The difference between a project and a component
    is that a project is the top-level node, and components are children of the project. There is also a category field
    that includes the option of project. The categorization essentially determines which icon is displayed by the
    Node in the front-end UI and helps with search organization. Top-level Nodes may have a category other than
    project, and children nodes may have a category of project.

    By default, a GET will return a list of public nodes, sorted by date_modified. You can filter Nodes by their title,
    description, and public fields.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
    )
    serializer_class = NodeSerializer
    ordering = ('-date_modified', )  # default ordering

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        base_query = (
            Q('is_deleted', 'ne', True) &
            Q('is_folder', 'ne', True)
        )
        user = self.request.user
        permission_query = Q('is_public', 'eq', True)
        if not user.is_anonymous():
            permission_query = (Q('is_public', 'eq', True) | Q('contributors', 'icontains', user._id))

        query = base_query & permission_query
        return query

    # overrides ListCreateAPIView
    def get_queryset(self):
        query = self.get_query_from_request()
        return Node.find(query)

    # overrides ListCreateAPIView
    def perform_create(self, serializer):
        """
        Create a node.
        """
        """
        :param serializer:
        :return:
        """
        # On creation, make sure that current user is the creator
        user = self.request.user
        serializer.save(creator=user)


class NodeDetail(generics.RetrieveUpdateAPIView, NodeMixin):
    """Projects and component details.

    On the front end, nodes are considered 'projects' or 'components'. The difference between a project and a component
    is that a project is the top-level node, and components are children of the project. There is also a category field
    that includes the option of project. The categorization essentially determines which icon is displayed by the
    Node in the front-end UI and helps with search organization. Top-level Nodes may have a category other than
    project, and children nodes may have a category of project.
    """
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


class NodeContributorsList(generics.ListAPIView, ListFilterMixin, NodeMixin):
    """Contributors (users) for a node.

    Contributors are users who can make changes to the node or, in the case of private nodes,
    have read access to the node. Contributors are divided between 'bibliographic' and 'non-bibliographic'
    contributors. From a permissions standpoint, both are the same, but bibliographic contributors
    are included in citations, while non-bibliographic contributors are not included in citations.
    """

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
    )

    serializer_class = ContributorSerializer

    def get_default_queryset(self):
        node = self.get_node()
        visible_contributors = node.visible_contributor_ids
        contributors = []
        for contributor in node.contributors:
            contributor.bibliographic = contributor._id in visible_contributors
            contributors.append(contributor)
        return contributors

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()


class NodeRegistrationsList(generics.ListAPIView, NodeMixin):
    """Registrations of the current node.

    Registrations are read-only snapshots of a project. This view lists all of the existing registrations
     created for the current node."""
    permission_classes = (
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
    )

    serializer_class = NodeSerializer

    # overrides ListAPIView
    def get_queryset(self):
        nodes = self.get_node().node__registrations
        user = self.request.user
        if user.is_anonymous():
            auth = Auth(None)
        else:
            auth = Auth(user)
        registrations = [node for node in nodes if node.can_view(auth)]
        return registrations


class NodeChildrenList(generics.ListAPIView, NodeMixin):
    """Children of the current node.

    This will get the next level of child nodes for the selected node if the current user has read access for those
    nodes. Currently, if there is a discrepancy between the children count and the number of children returned, it
    probably indicates private nodes that aren't being returned. That discrepancy should disappear before everything
    is finalized.
    """
    permission_classes = (
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
    )

    serializer_class = NodeSerializer

    # overrides ListAPIView
    def get_queryset(self):
        nodes = self.get_node().nodes
        user = self.request.user
        if user.is_anonymous():
            auth = Auth(None)
        else:
            auth = Auth(user)
        children = [node for node in nodes if node.can_view(auth) and node.primary]
        return children


class NodePointersList(generics.ListCreateAPIView, NodeMixin):
    """Pointers to other nodes.

    Pointers are essentially aliases or symlinks: All they do is point to another node.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
    )

    serializer_class = NodePointersSerializer

    def get_queryset(self):
        pointers = self.get_node().nodes_pointer
        return pointers


class NodePointerDetail(generics.RetrieveDestroyAPIView, NodeMixin):
    """Detail of a pointer to another node.

    Pointers are essentially aliases or symlinks: All they do is point to another node.
    """
    permission_classes = (
        ContributorOrPublicForPointers,
        drf_permissions.IsAuthenticatedOrReadOnly,
    )

    serializer_class = NodePointersSerializer

    # overrides RetrieveAPIView
    def get_object(self):
        pointer_lookup_url_kwarg = 'pointer_id'
        pointer = get_object_or_404(Pointer, self.kwargs[pointer_lookup_url_kwarg])
        # May raise a permission denied
        self.check_object_permissions(self.request, pointer)
        return pointer

    # overrides DestroyAPIView
    def perform_destroy(self, instance):
        user = self.request.user
        auth = Auth(user)
        node = self.get_node()
        pointer = self.get_object()
        node.rm_pointer(pointer, auth)
        node.save()


class NodeFilesList(generics.ListAPIView, NodeMixin):
    """Files attached to a node.

    This gives a list of all of the files that are on your project. Because this works with external services, some
    ours and some not, there is some extra data that you need for how to interact with those services.

    At the top level file list of your project you have a list of providers that are connected to this project. If you
    want to add more, you will need to do that in the Open Science Framework front end for now. For everything in the
    data.links dictionary, you'll have two types of fields: `self` and `related`. These are the same as everywhere else:
    self links are what you use to manipulate the object itself with GET, POST, DELETE, and PUT requests, while
    related links give you further data about that resource.

    So if you GET a self link for a file, it will return the file itself for downloading. If you GET a related link for
    a file, you'll get the metadata about the file. GETting a related link for a folder will get you the listing of
    what's in that folder. GETting a folder's self link won't work, because there's nothing to get.

    Which brings us to the other useful thing about the links here: there's a field called `self-methods`. This field
    will tell you what the valid methods are for the self links given the kind of thing they are (file vs folder) and
    given your permissions on the object.

    NOTE: Most of the API will be stable as far as how the links work because the things they are accessing are fairly
    stable and predictable, so if you felt the need, you could construct them in the normal REST way and they should
    be fine.
    The 'self' links from the NodeFilesList may have to change from time to time, so you are highly encouraged to use
    the links as we provide them before you use them, and not to reverse engineer the structure of the links as they
    are at any given time.
    """
    serializer_class = NodeFilesSerializer

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
    )

    def get_valid_self_link_methods(self, root_folder=False):
        valid_methods = {'file': ['GET'], 'folder': [], }
        user = self.request.user
        if user is None or user.is_anonymous():
            return valid_methods

        permissions = self.get_node().get_permissions(user)
        if 'write' in permissions:
            valid_methods['file'].append('POST')
            valid_methods['file'].append('DELETE')
            valid_methods['folder'].append('POST')
            if not root_folder:
                valid_methods['folder'].append('DELETE')

        return valid_methods

    def get_file_item(self, item, cookie, obj_args):
        file_item = {
            'valid_self_link_methods': self.get_valid_self_link_methods()[item['kind']],
            'provider': item['provider'],
            'path': item['path'],
            'name': item['name'],
            'node_id': self.get_node()._primary_key,
            'cookie': cookie,
            'args': obj_args,
            'waterbutler_type': 'file',
            'item_type': item['kind'],
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

    def get_queryset(self):
        query_params = self.request.query_params

        addons = self.get_node().get_addons()
        user = self.request.user
        cookie = None if self.request.user.is_anonymous() else user.get_or_create_cookie()
        node_id = self.get_node()._id
        obj_args = self.request.parser_context['args']

        provider = query_params.get('provider')
        path = query_params.get('path', '/')
        files = []

        if provider is None:
            valid_self_link_methods = self.get_valid_self_link_methods(True)
            for addon in addons:
                if addon.config.has_hgrid_files:
                    files.append({
                        'valid_self_link_methods': valid_self_link_methods['folder'],
                        'provider': addon.config.short_name,
                        'name': addon.config.short_name,
                        'path': path,
                        'node_id': node_id,
                        'cookie': cookie,
                        'args': obj_args,
                        'waterbutler_type': 'file',
                        'item_type': 'folder',
                        'metadata': {},
                    })
        else:
            url = waterbutler_url_for('data', provider, path, self.kwargs['pk'], cookie, obj_args)
            waterbutler_request = requests.get(url)
            if waterbutler_request.status_code == 401:
                raise PermissionDenied
            try:
                waterbutler_data = waterbutler_request.json()['data']
            except KeyError:
                raise ValidationError(detail='detail: Could not retrieve files information.')

            if isinstance(waterbutler_data, list):
                for item in waterbutler_data:
                    file = self.get_file_item(item, cookie, obj_args)
                    files.append(file)
            else:
                files.append(self.get_file_item(waterbutler_data, cookie, obj_args))

        return files