from rest_framework import generics, permissions as drf_permissions
from modularodm import Q

from website.models import User, Node
from framework.auth.core import Auth
from api.base.utils import get_object_or_404
from api.base.filters import ODMFilterMixin
from api.nodes.serializers import NodeSerializer
from .serializers import UserSerializer

class UserMixin(object):
    """Mixin with convenience methods for retrieving the current node based on the
    current URL. By default, fetches the user based on the pk kwarg.
    """

    serializer_class = UserSerializer
    node_lookup_url_kwarg = 'pk'

    def get_user(self, check_permissions=True):
        obj = get_object_or_404(User, self.kwargs[self.node_lookup_url_kwarg])
        if check_permissions:
            # May raise a permission denied
            self.check_object_permissions(self.request, obj)
        return obj


class UserList(generics.ListAPIView, ODMFilterMixin):
    """Users registered on the OSF.

    You can filter on users by their id, fullname, given_name, middle_name, or family_name.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
    )
    serializer_class = UserSerializer
    ordering = ('-date_registered')

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        return (
            Q('is_registered', 'eq', True) &
            Q('is_merged', 'ne', True) &
            Q('date_disabled', 'eq', None)
        )

    # overrides ListAPIView
    def get_queryset(self):
        # TODO: sort
        query = self.get_query_from_request()
        return User.find(query)


class UserDetail(generics.RetrieveAPIView, UserMixin):
    """Details about a specific user.
    """
    serializer_class = UserSerializer

    # overrides RetrieveAPIView
    def get_object(self):
        return self.get_user()


class UserNodes(generics.ListAPIView, UserMixin, ODMFilterMixin):
    """Nodes belonging to a user.

    Return a list of nodes that the user contributes to. """
    serializer_class = NodeSerializer

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        user = self.get_user(check_permissions=False)
        return (
            Q('contributors', 'eq', user) &
            Q('is_folder', 'ne', True) &
            Q('is_deleted', 'ne', True)
        )

    # overrides ListAPIView
    def get_queryset(self):
        current_user = self.request.user
        if current_user.is_anonymous():
            auth = Auth(None)
        else:
            auth = Auth(current_user)
        query = self.get_query_from_request()
        raw_nodes = Node.find(self.get_default_odm_query() & query)
        nodes = [each for each in raw_nodes if each.is_public or each.can_view(auth)]
        return nodes
