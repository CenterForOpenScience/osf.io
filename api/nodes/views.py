from rest_framework import generics, permissions as drf_permissions
from modularodm import Q

from framework.auth.core import Auth
from website.models import Node, Pointer
from api.base.utils import get_object_or_404
from api.base.filters import ODMFilterMixin
from .serializers import NodeSerializer, NodePointersSerializer
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
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
    )
    serializer_class = NodeSerializer
    ordering = ('-date_modified', )  # default ordering

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        return (
            Q('is_public', 'eq', True) &
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


class NodePointersList(generics.ListCreateAPIView, NodeMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
    )

    serializer_class = NodePointersSerializer

    def get_queryset(self):
        return self.get_node().nodes_pointer


class NodePointerDetail(generics.RetrieveDestroyAPIView, NodeMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
    )

    serializer_class = NodePointersSerializer

    # overrides RetrieveAPIView
    def get_object(self):
        pointer_lookup_url_kwarg = 'pointer_id'
        pointer = get_object_or_404(Pointer, self.kwargs[pointer_lookup_url_kwarg])
        return pointer

    # overrides DestroyAPIView
    def perform_destroy(self, instance):
        user = self.request.user
        auth = Auth(user)
        node = self.get_node()
        pointer = self.get_object()
        node.rm_pointer(pointer, auth)
        node.save()