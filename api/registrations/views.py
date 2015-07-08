
from rest_framework import status
from rest_framework.response import Response
from rest_framework import generics, permissions as drf_permissions

from modularodm import Q
from website.models import Node
from api.nodes.views import NodeMixin
from api.base.filters import ODMFilterMixin
from website.language import REGISTER_WARNING
from api.nodes.serializers import NodeSerializer
from api.base.utils import token_creator, absolute_reverse
from api.draft_registrations.views import DraftRegistrationMixin
from api.nodes.permissions import ContributorOrPublic, ReadOnlyIfRegistration
from api.registrations.serializers import RegistrationCreateSerializer, RegistrationCreateSerializerWithToken


class RegistrationList(generics.ListAPIView, ODMFilterMixin):
    """All node registrations"""

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
    )
    serializer_class = NodeSerializer

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        base_query = (
            Q('is_deleted', 'ne', True) &
            Q('is_folder', 'ne', True) &
            (Q('is_registration', 'eq', True))
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


class RegistrationCreate(generics.CreateAPIView, DraftRegistrationMixin):
    "Turn a draft registration into a frozen registration"
    permission_classes = (
        ContributorOrPublic,
    )

    serializer_class = RegistrationCreateSerializer

    def create(self, request, draft_id):
        user = request.user
        draft = self.get_draft()
        token = token_creator(draft._id, user._id)
        url = absolute_reverse('registrations:registration-create', kwargs={'draft_id': draft._id, 'token': token})
        registration_warning = REGISTER_WARNING.format((draft.title))
        return Response({'data': {'id': draft._id, 'warning_message': registration_warning, 'links': {'confirm_register': url}}}, status=status.HTTP_202_ACCEPTED)


class RegistrationCreateWithToken(generics.CreateAPIView, NodeMixin):
    """
    Save your registration draft
    """
    permission_classes = (
        ContributorOrPublic,
        ReadOnlyIfRegistration,
    )

    serializer_class = RegistrationCreateSerializerWithToken
