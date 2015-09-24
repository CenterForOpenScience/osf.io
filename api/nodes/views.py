import requests

from modularodm import Q
from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound

from framework.auth.core import Auth
from framework.auth.oauth_scopes import CoreScopes

from api.base import permissions as base_permissions
from api.base.filters import ODMFilterMixin, ListFilterMixin
from api.base.utils import get_object_or_error
from api.files.serializers import FileSerializer
from api.users.views import UserMixin
from api.nodes.serializers import (
    NodeSerializer,
    NodeLinksSerializer,
    NodeDetailSerializer,
    NodeProviderSerializer,
    NodeContributorsSerializer,
    NodeRegistrationSerializer,
    NodeContributorDetailSerializer
)
from api.nodes.permissions import (
    AdminOrPublic,
    ContributorOrPublic,
    ContributorOrPublicForPointers,
    ContributorDetailPermissions,
    ReadOnlyIfRegistration,
)

from website.exceptions import NodeStateError
from website.files.models import FileNode
from website.files.models import OsfStorageFileNode
from website.models import Node, Pointer
from website.util import waterbutler_api_url_for


class NodeMixin(object):
    """Mixin with convenience methods for retrieving the current node based on the
    current URL. By default, fetches the current node based on the node_id kwarg.
    """

    serializer_class = NodeSerializer
    node_lookup_url_kwarg = 'node_id'

    def get_node(self, check_object_permissions=True):
        node = get_object_or_error(
            Node,
            self.kwargs[self.node_lookup_url_kwarg],
            display_name='node'
        )
        # Nodes that are folders/collections are treated as a separate resource, so if the client
        # requests a collection through a node endpoint, we return a 404
        if node.is_folder:
            raise NotFound
        # May raise a permission denied
        if check_object_permissions:
            self.check_object_permissions(self.request, node)
        return node

class WaterButlerMixin(object):

    path_lookup_url_kwarg = 'path'
    provider_lookup_url_kwarg = 'provider'

    def get_file_item(self, item):
        file_node = FileNode.resolve_class(
            item['provider'],
            FileNode.FOLDER if item['kind'] == 'folder'
            else FileNode.FILE
        ).get_or_create(self.get_node(check_object_permissions=False), item['path'])

        file_node.update(None, item, user=self.request.user)

        self.check_object_permissions(self.request, file_node)

        return file_node

    def fetch_from_waterbutler(self):
        node = self.get_node(check_object_permissions=False)
        path = self.kwargs[self.path_lookup_url_kwarg]
        provider = self.kwargs[self.provider_lookup_url_kwarg]

        if provider == 'osfstorage':
            # Kinda like /me for a user
            # The one odd case where path is not really path
            if path == '/':
                obj = node.get_addon('osfstorage').get_root()
            else:
                obj = get_object_or_error(
                    OsfStorageFileNode,
                    Q('node', 'eq', node._id) &
                    Q('_id', 'eq', path.strip('/')) &
                    Q('is_file', 'eq', not path.endswith('/'))
                )

            self.check_object_permissions(self.request, obj)

            return obj

        url = waterbutler_api_url_for(node._id, provider, path, meta=True)

        waterbutler_request = requests.get(
            url,
            cookies=self.request.COOKIES,
            headers={'Authorization': self.request.META.get('HTTP_AUTHORIZATION')},
        )

        if waterbutler_request.status_code == 401:
            raise PermissionDenied

        if waterbutler_request.status_code == 404:
            raise NotFound

        try:
            return waterbutler_request.json()['data']
        except KeyError:
            raise ValidationError(detail='detail: Could not retrieve files information.')


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
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NODE_BASE_WRITE]

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
        """Create a node.

        :param serializer:
        """
        # On creation, make sure that current user is the creator
        user = self.request.user
        serializer.save(creator=user)


class NodeDetail(generics.RetrieveUpdateDestroyAPIView, NodeMixin):
    """Projects and component details.

    On the front end, nodes are considered 'projects' or 'components'. The difference between a project and a component
    is that a project is the top-level node, and components are children of the project. There is also a category field
    that includes the option of project. The categorization essentially determines which icon is displayed by the
    Node in the front-end UI and helps with search organization. Top-level Nodes may have a category other than
    project, and children nodes may have a category of project.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        ReadOnlyIfRegistration,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NODE_BASE_WRITE]

    serializer_class = NodeDetailSerializer

    # overrides RetrieveUpdateDestroyAPIView
    def get_object(self):
        return self.get_node()

    # overrides RetrieveUpdateDestroyAPIView
    def get_serializer_context(self):
        # Serializer needs the request in order to make an update to privacy
        # TODO: The method it overrides already returns request (plus more stuff). Why does this method exist?
        return {'request': self.request}

    # overrides RetrieveUpdateDestroyAPIView
    def perform_destroy(self, instance):
        user = self.request.user
        auth = Auth(user)
        node = self.get_object()
        try:
            node.remove_node(auth=auth)
        except NodeStateError as err:
            raise ValidationError(err.message)
        node.save()


class NodeContributorsList(generics.ListCreateAPIView, ListFilterMixin, NodeMixin):
    """Contributors (users) for a node.

    Contributors are users who can make changes to the node or, in the case of private nodes,
    have read access to the node. Contributors are divided between 'bibliographic' and 'non-bibliographic'
    contributors. From a permissions standpoint, both are the same, but bibliographic contributors
    are included in citations, while non-bibliographic contributors are not included in citations.
    """
    permission_classes = (
        AdminOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        ReadOnlyIfRegistration,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_CONTRIBUTORS_READ]
    required_write_scopes = [CoreScopes.NODE_CONTRIBUTORS_WRITE]

    serializer_class = NodeContributorsSerializer

    def get_default_queryset(self):
        node = self.get_node()
        visible_contributors = node.visible_contributor_ids
        contributors = []
        for contributor in node.contributors:
            contributor.bibliographic = contributor._id in visible_contributors
            contributor.permission = node.get_permissions(contributor)[-1]
            contributor.node_id = node._id
            contributors.append(contributor)
        return contributors

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()


class NodeContributorDetail(generics.RetrieveUpdateDestroyAPIView, NodeMixin, UserMixin):
    """Detail of a contributor for a node.

    View, remove from, and change bibliographic and permissions for a given contributor on a given node.
    """
    permission_classes = (
        ContributorDetailPermissions,
        drf_permissions.IsAuthenticatedOrReadOnly,
        ReadOnlyIfRegistration,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_CONTRIBUTORS_READ]
    required_write_scopes = [CoreScopes.NODE_CONTRIBUTORS_WRITE]

    serializer_class = NodeContributorDetailSerializer

    # overrides RetrieveAPIView
    def get_object(self):
        node = self.get_node()
        user = self.get_user()
        # May raise a permission denied
        self.check_object_permissions(self.request, user)
        if user not in node.contributors:
            raise NotFound('{} cannot be found in the list of contributors.'.format(user))
        user.permission = node.get_permissions(user)[-1]
        user.bibliographic = node.get_visible(user)
        user.node_id = node._id
        return user

    # overrides DestroyAPIView
    def perform_destroy(self, instance):
        node = self.get_node()
        current_user = self.request.user
        auth = Auth(current_user)
        if len(node.visible_contributors) == 1 and node.get_visible(instance):
            raise ValidationError("Must have at least one visible contributor")
        removed = node.remove_contributor(instance, auth)
        if not removed:
            raise ValidationError("Must have at least one registered admin contributor")


# TODO: Support creating registrations
class NodeRegistrationsList(generics.ListAPIView, NodeMixin):
    """Registrations of the current node.

    Registrations are read-only snapshots of a project. This view lists all of the existing registrations
    created for the current node.
     """
    permission_classes = (
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NODE_REGISTRATIONS_WRITE]

    serializer_class = NodeRegistrationSerializer

    # overrides ListAPIView
    # TODO: Filter out retractions by default
    def get_queryset(self):
        nodes = self.get_node().node__registrations
        user = self.request.user
        if user.is_anonymous():
            auth = Auth(None)
        else:
            auth = Auth(user)
        registrations = [node for node in nodes if node.can_view(auth)]
        return registrations


class NodeChildrenList(generics.ListCreateAPIView, NodeMixin, ODMFilterMixin):
    """Children of the current node.

    This will get the next level of child nodes for the selected node if the current user has read access for those
    nodes. Currently, if there is a discrepancy between the children count and the number of children returned, it
    probably indicates private nodes that aren't being returned. That discrepancy should disappear before everything
    is finalized.
    """
    permission_classes = (
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        ReadOnlyIfRegistration,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_CHILDREN_READ]
    required_write_scopes = [CoreScopes.NODE_CHILDREN_WRITE]

    serializer_class = NodeSerializer

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        return (
            Q('is_deleted', 'ne', True) &
            Q('is_folder', 'ne', True)
        )

    # overrides ListAPIView
    def get_queryset(self):
        node = self.get_node()
        req_query = self.get_query_from_request()

        query = (
            Q('_id', 'in', [e._id for e in node.nodes if e.primary]) &
            req_query
        )
        nodes = Node.find(query)
        user = self.request.user
        if user.is_anonymous():
            auth = Auth(None)
        else:
            auth = Auth(user)
        children = [each for each in nodes if each.can_view(auth)]
        return children

    # overrides ListCreateAPIView
    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(creator=user, parent=self.get_node())


# TODO: Make NodeLinks filterable. They currently aren't filterable because we have can't
# currently query on a Pointer's node's attributes.
# e.g. Pointer.find(Q('node.title', 'eq', ...)) doesn't work
class NodeLinksList(generics.ListCreateAPIView, NodeMixin):
    """Node Links to other nodes.

    Node Links act as pointers to other nodes. Unlike Forks, they are not copies of nodes;
    Node Links are a direct reference to the node that they point to.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        ReadOnlyIfRegistration,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_LINKS_READ]
    required_write_scopes = [CoreScopes.NODE_LINKS_WRITE]

    serializer_class = NodeLinksSerializer

    def get_queryset(self):
        return [
            pointer for pointer in
            self.get_node().nodes_pointer
            if not pointer.node.is_deleted
        ]


class NodeLinksDetail(generics.RetrieveDestroyAPIView, NodeMixin):
    """Node Link details.

    Node Links act as pointers to other nodes. Unlike Forks, they are not copies of nodes;
    Node Links are a direct reference to the node that they point to.
    """
    permission_classes = (
        ContributorOrPublicForPointers,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ReadOnlyIfRegistration,
    )

    required_read_scopes = [CoreScopes.NODE_LINKS_READ]
    required_write_scopes = [CoreScopes.NODE_LINKS_WRITE]

    serializer_class = NodeLinksSerializer

    # overrides RetrieveAPIView
    def get_object(self):
        node_link_lookup_url_kwarg = 'node_link_id'
        node_link = get_object_or_error(
            Pointer,
            self.kwargs[node_link_lookup_url_kwarg],
            'node link'
        )
        # May raise a permission denied
        self.check_object_permissions(self.request, node_link)
        return node_link

    # overrides DestroyAPIView
    def perform_destroy(self, instance):
        user = self.request.user
        auth = Auth(user)
        node = self.get_node()
        pointer = self.get_object()
        try:
            node.rm_pointer(pointer, auth=auth)
        except ValueError as err:  # pointer doesn't belong to node
            raise ValidationError(err.message)
        node.save()


class NodeFilesList(generics.ListAPIView, WaterButlerMixin, NodeMixin):
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
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.PermissionWithGetter(ContributorOrPublic, 'node'),
        base_permissions.PermissionWithGetter(ReadOnlyIfRegistration, 'node'),
        base_permissions.TokenHasScope,
    )

    serializer_class = FileSerializer

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NODE_FILE_WRITE]

    def get_queryset(self):
        # Don't bother going to waterbutler for osfstorage
        files_list = self.fetch_from_waterbutler()

        if isinstance(files_list, list):
            return [self.get_file_item(file) for file in files_list]

        if isinstance(files_list, dict) or getattr(files_list, 'is_file', False):
            # We should not have gotten a file here
            raise NotFound

        return list(files_list.children)


class NodeFileDetail(generics.RetrieveAPIView, WaterButlerMixin, NodeMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.PermissionWithGetter(ContributorOrPublic, 'node'),
        base_permissions.PermissionWithGetter(ReadOnlyIfRegistration, 'node'),
        base_permissions.TokenHasScope,
    )

    serializer_class = FileSerializer

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NODE_FILE_WRITE]

    def get_object(self):
        fobj = self.fetch_from_waterbutler()
        if isinstance(fobj, dict):
            return self.get_file_item(fobj)

        if isinstance(fobj, list) or not getattr(fobj, 'is_file', True):
            # We should not have gotten a folder here
            raise NotFound

        return fobj


class NodeProvider(object):

    def __init__(self, provider, node):
        self.path = '/'
        self.node = node
        self.kind = 'folder'
        self.name = provider
        self.provider = provider
        self.node_id = node._id
        self.pk = node._id


class NodeProvidersList(generics.ListAPIView, NodeMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NODE_FILE_WRITE]

    serializer_class = NodeProviderSerializer

    def get_provider_item(self, provider):
        return NodeProvider(provider, self.get_node())

    def get_queryset(self):
        return [
            self.get_provider_item(addon.config.short_name)
            for addon
            in self.get_node().get_addons()
            if addon.config.has_hgrid_files
            and addon.complete
        ]
