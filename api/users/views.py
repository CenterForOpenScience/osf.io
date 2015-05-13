from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import PermissionDenied
from modularodm import Q

from website.models import User, Node, OAuth2App
from framework.auth.core import Auth
from api.base.utils import get_object_or_404
from api.base.filters import ODMFilterMixin
from api.nodes.serializers import NodeSerializer
from .serializers import OAuth2AppSerializer, UserSerializer

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
    """Return a list of registered users.

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

    serializer_class = UserSerializer

    # overrides RetrieveAPIView
    def get_object(self):
        return self.get_user()


class UserNodes(generics.ListAPIView, UserMixin, ODMFilterMixin):
    """Get a user's nodes.

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
        user = self.get_user(check_permissions=False)
        current_user = self.request.user
        if user.is_anonymous():
            auth = Auth(None)
        else:
            auth = Auth(current_user)
        query = self.get_query_from_request()
        nodes = [
            each for each in
            Node.find(self.get_default_odm_query() & query)
            if each.is_public or each.can_view(auth)
        ]
        return nodes


# TODO: Needs to also handle a PUT or POST request for creating new single instances via this url:
#       Possible alternate parent classes in http://www.django-rest-framework.org/api-guide/generic-views/#listapiview
class ApplicationList(generics.ListAPIView, ODMFilterMixin):
    """
    Get a list of API applications (eg OAuth2) that the user has registered

    Will only return success if logged in as that specified user
    """
    permission_classes = (
        drf_permissions.IsAuthenticated,
    )

    serializer_class = OAuth2AppSerializer

    # Revisit whether this is the best way to enforce user = logged in user
    def get_default_odm_query(self):

        return (
            Q('owner', 'eq', self.request.user) &
            Q('active', 'eq', True)
        )

    # overrides ListAPIView
    def get_queryset(self):
        query = self.get_query_from_request()
        return OAuth2App.find(query)


class ApplicationDetail(generics.RetrieveUpdateDestroyAPIView, ):
    """
    Get information about a specific API application (eq OAuth2) that the user has registered

    Will only return success if logged in as that specified user
    """

    permission_classes = (
        drf_permissions.IsAuthenticated,
    )

    serializer_class = OAuth2AppSerializer

    # overrides RetrieveAPIView
    def get_object(self):
        id_url_kwarg = 'client_id'
        print "---- DEBUGGING   ", self.kwargs[id_url_kwarg], "KW", self.kwargs
        query = Q('client_id', 'eq', self.kwargs[id_url_kwarg])
        obj = get_object_or_404(OAuth2App, query)

        # TODO: Write test for case where user is not logged in, or wrong user requests resource
        if obj.owner._id != self.request.user._id:
            raise PermissionDenied

        return obj
