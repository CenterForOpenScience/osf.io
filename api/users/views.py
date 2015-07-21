from rest_framework import generics, permissions as drf_permissions
from rest_framework.response import Response
from modularodm import Q

from website.models import User, Node
from framework.auth.core import Auth
from api.base.utils import get_object_or_404
from rest_framework.exceptions import NotFound

#todo move get_user_auth?
from api.nodes.permissions import get_user_auth
from api.base.filters import ODMFilterMixin
from api.nodes.serializers import NodeSerializer
from api.nodes.views import NodeIncludeMixin
from .serializers import UserSerializer

class UserMixin(object):
    """Mixin with convenience methods for retrieving the current node based on the
    current URL. By default, fetches the user based on the pk kwarg.
    """

    serializer_class = UserSerializer
    node_lookup_url_kwarg = 'user_id'

    def get_user(self, check_permissions=True, get_additional_params=True):
        obj = get_object_or_404(User, self.kwargs[self.node_lookup_url_kwarg])
        if check_permissions:
            # May raise a permission denied
            self.check_object_permissions(self.request, obj)
        if get_additional_params:
            obj = self.get_additional_parameters(self.request, obj)
        return obj

class UserIncludeMixin(object):

    def get_additional_parameters(self, request, user):
        if 'include' in request.query_params:
            parameters = request.query_params['include'].split(',')
            auth = get_user_auth(request)
            if 'nodes' in parameters:
                user.nodes = [node for node in user.node__contributed if node.can_view(auth)]
                parameters.remove('nodes')
            if parameters != []:
                raise NotFound('{} are not valid parameters.'.format(parameters))
        return user


class UserList(generics.ListAPIView, ODMFilterMixin, UserIncludeMixin):
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

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        users = []
        page = self.paginate_queryset(queryset)
        for user in page:
            user = self.get_additional_parameters(request, user)
            users.append(user)
        if page is not None:
            serializer = self.get_serializer(users, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class UserDetail(generics.RetrieveAPIView, UserMixin, UserIncludeMixin):
    """Details about a specific user.
    """
    serializer_class = UserSerializer

    # overrides RetrieveAPIView
    def get_object(self):
        return self.get_user()

# todo, modify mixin
class UserNodes(generics.ListAPIView, UserMixin, ODMFilterMixin, NodeIncludeMixin):
    """Nodes belonging to a user.

    Return a list of nodes that the user contributes to. """
    serializer_class = NodeSerializer

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        user = self.get_user(check_permissions=False, get_additional_params=False)
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
        nodes = []
        for node in raw_nodes:
            if node.is_public or node.can_view(auth):
                node = self.get_additional_parameters(self.request, node)
                nodes.append(node)
        return nodes
