import requests

from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from modularodm import Q

from framework.auth.core import Auth
from website.models import Node, Pointer
from api.base.utils import get_object_or_404, waterbutler_url_for
from api.base.filters import ODMFilterMixin, ListFilterMixin
from api.registrations.serializers import RegistrationSerializer
from api.users.serializers import ContributorSerializer
from api.nodes.permissions import ContributorOrPublic, ReadOnlyIfRegistration, ContributorOrPublicForPointers


class NodeRegistrationsAll(generics.ListAPIView, ODMFilterMixin):
    """Node registrations"""

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

