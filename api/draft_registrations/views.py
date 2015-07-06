from framework.auth.core import Auth

from rest_framework import status
from rest_framework.response import Response
from rest_framework import generics, permissions as drf_permissions

from modularodm import Q
from website.models import DraftRegistration
from api.base.utils import get_object_or_404
from api.base.filters import ODMFilterMixin
from api.nodes.permissions import ContributorOrPublic
from api.draft_registrations.serializers import DraftRegSerializer
from rest_framework.exceptions import NotAuthenticated


class DraftRegistrationMixin(object):
    """Mixin with convenience methods for retrieving the current draft based on the
    current URL. By default, fetches the current draft based on the id kwarg.
    """

    serializer_class = DraftRegSerializer
    draft_lookup_url_kwarg = 'registration_id'


    def get_draft(self):
        obj = get_object_or_404(DraftRegistration, self.kwargs[self.draft_lookup_url_kwarg])
        # May raise a permission denied
        self.check_object_permissions(self.request, obj)
        return obj


class DraftRegistrationList(generics.ListAPIView, ODMFilterMixin):
    """All draft registrations"""

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
    )
    serializer_class = DraftRegSerializer

    # overrides ListAPIView
    def get_queryset(self):
        user = self.request.user
        if user.is_anonymous():
            raise NotAuthenticated("Must be logged in to view draft registrations")
        return DraftRegistration.find(Q('initiator', 'eq', user))


 # permission_classes = (
 #        drf_permissions.IsAuthenticatedOrReadOnly,
 #    )
 #    serializer_class = NodeSerializer
 #    ordering = ('-date_modified', )  # default ordering
 #
 #    # overrides ODMFilterMixin
 #    def get_default_odm_query(self):
 #        base_query = (
 #            Q('is_deleted', 'ne', True) &
 #            Q('is_folder', 'ne', True)
 #        )
 #        user = self.request.user
 #        permission_query = Q('is_public', 'eq', True)
 #        if not user.is_anonymous():
 #            permission_query = (Q('is_public', 'eq', True) | Q('contributors', 'icontains', user._id))
 #
 #        query = base_query & permission_query
 #        return query
 #
 #    # overrides ListCreateAPIView
 #    def get_queryset(self):
 #        query = self.get_query_from_request()
 #        return Node.find(query)
 #
 #    # overrides ListCreateAPIView
 #    def perform_create(self, serializer):
 #        """
 #        Create a node.
 #        """
 #        """
 #        :param serializer:
 #        :return:
 #        """
 #        # On creation, make sure that current user is the creator
 #        user = self.request.user
 #        serializer.save(creator=user)

class DraftRegistrationDetail(generics.RetrieveUpdateDestroyAPIView, DraftRegistrationMixin):
    """
    Draft Registration details
    """
    permission_classes = (
        ContributorOrPublic,
    )

    serializer_class = DraftRegSerializer

    # Restores original get_serializer_class
    def get_serializer_context(self):
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }

    # overrides RetrieveUpdateDestroyAPIView
    def get_object(self):
        draft = self.get_draft()
        return draft

    # overrides RetrieveUpdateDestroyAPIView
    def perform_destroy(self, instance):
        user = self.request.user
        auth = Auth(user)
        draft = self.get_object()
        draft.remove_node(auth=auth)
        draft.save()

