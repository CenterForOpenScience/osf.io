from framework.auth.core import Auth

from rest_framework.exceptions import NotAuthenticated
from rest_framework import generics, permissions as drf_permissions

from modularodm import Q
from api.base.filters import ODMFilterMixin
from website.models import DraftRegistration
from api.base.utils import get_object_or_404
from api.nodes.permissions import ContributorOrPublic
from api.draft_registrations.serializers import DraftRegSerializer


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

