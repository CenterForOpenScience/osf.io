from rest_framework import generics, permissions as drf_permissions
from modularodm import Q
from datetime import datetime

from framework.auth.core import Auth
from website.models import Node, Pointer
from api.base.utils import get_object_or_404
from api.base.filters import ODMFilterMixin, ListFilterMixin
from .serializers import CollectionSerializer, CollectionPointersSerializer
from .permissions import ReadOnlyIfRegistration, ContributorOrPublic
from website.views import _render_nodes, find_dashboard


class CollectionMixin(object):
    """Mixin with convenience methods for retrieving the current node based on the
    current URL. By default, fetches the current node based on the pk kwarg.
    """

    serializer_class = CollectionSerializer
    node_lookup_url_kwarg = 'pk'

    def get_node(self):
        key = self.kwargs[self.node_lookup_url_kwarg]
        if key == 'dashboard':
            return find_dashboard(self.request.user)

        obj = get_object_or_404(Node, key)
        # May raise a permission denied
        self.check_object_permissions(self.request, obj)
        return obj


class CollectionList(generics.ListCreateAPIView, ListFilterMixin, ODMFilterMixin):
    """Projects and components.

    By default, a GET will return a list of collections, sorted by date_modified. You can filter Collection by their
    title. Note that you must be logged in to access it
    """
    permission_classes = (
        drf_permissions.IsAuthenticated,
    )
    serializer_class = CollectionSerializer
    ordering = ('-date_modified',)  # default ordering

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        user = self.request.user
        base_query = (
            Q('is_deleted', 'ne', True) &
            Q('is_folder', 'eq', True) &
            Q('contributors', 'icontains', user._id)
        )

        return base_query

    # overrides ListCreateAPIView
    def get_queryset(self):
        query = self.get_query_from_request()
        nodes = Node.find(query)

        for node in nodes:
            node.smart_folder = False

        return nodes

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


class DashboardDetail(generics.ListCreateAPIView, ODMFilterMixin):
    """Projects and components.

    By default, a GET will return a user's dashboard. Note that you must be logged in to access it
    """

    permission_classes = (
        drf_permissions.IsAuthenticated,
    )
    serializer_class = CollectionSerializer
    ordering = ('-date_modified',)  # default ordering

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        base_query = (
            Q('is_deleted', 'ne', True) &
            Q('is_dashboard', 'eq', True)
        )

        return base_query

    # overrides ListCreateAPIView
    def get_queryset(self):
        query = self.get_query_from_request()
        nodes = Node.find(query)

        for node in nodes:
            node.smart_folder = False

        return nodes

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


class CollectionDetail(generics.RetrieveUpdateAPIView, generics.RetrieveDestroyAPIView,
                       CollectionMixin):
    """Collection detail

    """

    def get_object(self):
        node = self.get_node()
        node.smart_folder = False
        return node

    permission_classes = (
        drf_permissions.IsAuthenticated,
    )
    serializer_class = CollectionSerializer

    # overrides RetrieveUpdateAPIView
    def get_serializer_context(self):
        # Serializer needs the request in order to make an update to privacy
        return {'request': self.request}

    # overrides DestroyAPIView
    def perform_destroy(self, instance):
        user = self.request.user
        auth = Auth(user)
        node = self.get_node()
        date = datetime.now()
        # Right now you cannot DELETE the dashboard but if you try, you get a 204
        if not node.is_dashboard:
            node.remove_node(auth, date)
        node.save()


class CollectionChildrenList(generics.ListAPIView, CollectionMixin):
    """Children of the current collection.

    This will get the next level of child nodes for the selected collection if the current user has read access for those
    nodes. Currently, if there is a discrepancy between the children count and the number of children returned, it
    probably indicates private nodes that aren't being returned. That discrepancy should disappear before everything
    is finalized.
    """
    permission_classes = (
        drf_permissions.IsAuthenticated,
        ContributorOrPublic
    )

    serializer_class = CollectionSerializer

    # overrides ListAPIView
    def get_queryset(self):

        smart_folders = (
            '~amr',
            '~amp',
        )
        nodes = self.get_node().nodes
        smart_folder_nodes = []
        for node in nodes:
            node_id = self.kwargs[self.node_lookup_url_kwarg]
            for folder_id in smart_folders:
                if node_id == folder_id:
                    spoof_node = Node.find(node_id)
                    smart_folder_node = {
                        'id': spoof_node._id,
                        'title': spoof_node.title,
                        'date_created': spoof_node.date_created,
                        'date_modified': spoof_node.date_modified,
                        'properties': {
                            'smart_folder': True,
                        },
                    }
                    smart_folder_nodes.append(smart_folder_node)

        user = self.request.user
        if user.is_anonymous():
            auth = Auth(None)
        else:
            auth = Auth(user)
        children = [node for node in nodes if node.can_view(auth)]
        return children


class CollectionPointersList(generics.ListCreateAPIView, CollectionMixin):
    """Pointers to other nodes.

    Pointers are essentially aliases or symlinks: All they do is point to another node.
    """
    permission_classes = (
        drf_permissions.IsAuthenticated,
        ContributorOrPublic,
    )

    serializer_class = CollectionPointersSerializer

    def get_queryset(self):
        pointers = self.get_node().nodes_pointer
        return pointers


class CollectionPointerDetail(generics.RetrieveDestroyAPIView, CollectionMixin):
    """Detail of a pointer to another node.

    Pointers are essentially aliases or symlinks: All they do is point to another node.
    """
    permission_classes = (
        drf_permissions.IsAuthenticated,
        ContributorOrPublic,
    )

    serializer_class = CollectionPointersSerializer

    # overrides RetrieveAPIView
    def get_object(self):
        pointer_lookup_url_kwarg = 'pointer_id'
        pointer = get_object_or_404(Pointer, self.kwargs[pointer_lookup_url_kwarg])
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
