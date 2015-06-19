from rest_framework import generics, permissions as drf_permissions
from modularodm import Q

from website.models import Node
from api.base.filters import ODMFilterMixin
from api.registrations.serializers import RegistrationSerializer
from api.nodes.views import NodeDetail, NodePointersList, NodeFilesList, NodeChildrenList, NodeContributorsList


class RegistrationList(generics.ListAPIView, ODMFilterMixin):
    """All node registrations"""

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
    )
    serializer_class = RegistrationSerializer

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        base_query = (
            Q('is_deleted', 'ne', True) &
            Q('is_folder', 'ne', True) &
            Q('is_registration', 'eq', True)
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


class RegistrationDetail(NodeDetail):
    """
    Registration details
    """


class RegistrationPointersList(NodePointersList):
     """
    Registration pointers
    """


class RegistrationFilesList(NodeFilesList):
     """
    Files attached to a registration
    """


class RegistrationChildrenList(NodeChildrenList):
    """
    Children of the current registration
    """


class RegistrationContributorsList(NodeContributorsList):
    """
    Contributors(users) for a registration
    """
