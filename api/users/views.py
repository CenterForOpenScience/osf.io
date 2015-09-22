from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import NotAuthenticated
from django.contrib.auth.models import AnonymousUser

from modularodm import Q

from framework.auth.core import Auth
from framework.auth.oauth_scopes import CoreScopes

from website.models import User, Node

from api.base import permissions as base_permissions
from api.base.utils import get_object_or_error
from api.base.filters import ODMFilterMixin
from api.nodes.serializers import NodeSerializer

from .serializers import UserSerializer, UserDetailSerializer
from .permissions import ReadOnlyOrCurrentUser


class UserMixin(object):
    """Mixin with convenience methods for retrieving the current node based on the
    current URL. By default, fetches the user based on the user_id kwarg.
    """

    serializer_class = UserSerializer
    user_lookup_url_kwarg = 'user_id'

    def get_user(self, check_permissions=True):
        key = self.kwargs[self.user_lookup_url_kwarg]
        current_user = self.request.user

        if key == 'me':
            if isinstance(current_user, AnonymousUser):
                raise NotAuthenticated
            else:
                return self.request.user

        obj = get_object_or_error(User, key, 'user')
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
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.USERS_READ]
    required_write_scopes = [CoreScopes.USERS_WRITE]

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


class UserDetail(generics.RetrieveUpdateAPIView, UserMixin):
    """Details about a specific user.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ReadOnlyOrCurrentUser,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.USERS_READ]
    required_write_scopes = [CoreScopes.USERS_WRITE]

    serializer_class = UserDetailSerializer

    # overrides RetrieveAPIView
    def get_object(self):
        return self.get_user()

    # overrides RetrieveUpdateAPIView
    def get_serializer_context(self):
        # Serializer needs the request in order to make an update to privacy
        return {'request': self.request}


class UserNodes(generics.ListAPIView, UserMixin, ODMFilterMixin):
    """Nodes belonging to a user.
    Return a list of nodes that the user contributes to.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.USERS_READ, CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.USERS_WRITE, CoreScopes.NODE_BASE_WRITE]

    serializer_class = NodeSerializer

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        user = self.get_user()
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
