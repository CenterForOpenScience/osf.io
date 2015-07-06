
from rest_framework import status
from rest_framework.response import Response
from django.utils.translation import ugettext_lazy as _
from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import ValidationError

from modularodm import Q
from website.models import Node
from api.base.filters import ODMFilterMixin
from website.language import REGISTER_WARNING
from api.base.utils import token_creator, absolute_reverse
from api.nodes.permissions import ContributorOrPublic, ReadOnlyIfRegistration
from api.nodes.views import NodeMixin, NodeDetail
from api.registrations.serializers import RegistrationSerializer, RegistrationCreateSerializer, RegistrationCreateSerializerWithToken


def registration_enforcer(node):
    if node.is_registration is False and node.is_registration_draft is False:
        raise ValidationError(_('Not a registration or registration draft.'))


class RegistrationMixin(NodeMixin):
    """Mixin with convenience methods for retrieving the current node based on the
    current URL. By default, fetches the current node based on the pk kwarg.
    """

    serializer_class = RegistrationSerializer
    node_lookup_url_kwarg = 'registration_id'


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


class RegistrationDetail(NodeDetail, generics.CreateAPIView, RegistrationMixin):
    """
    Registration details
    """
    permission_classes = (
        ContributorOrPublic,
        ReadOnlyIfRegistration,
    )

    def get_serializer_class(self):
        if self.request.method == 'POST':
            serializer_class = RegistrationCreateSerializer
            return serializer_class
        serializer_class = RegistrationSerializer
        return serializer_class

    # Restores original get_serializer_class
    def get_serializer_context(self):
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }

    # overrides RetrieveAPIView
    def get_object(self):
        node = self.get_node()
        registration_enforcer(node)
        return self.get_node()

    # overrides CreateAPIView
    def create(self, request, registration_id):
        user = request.user
        node = self.get_node()
        if node.is_registration_draft is False:
            raise ValidationError(_('Not a registration draft.'))
        token = token_creator(node._id, user._id)
        url = absolute_reverse('registrations:registration-create', kwargs={'registration_id': node._id, 'token': token})
        registration_warning = REGISTER_WARNING.format((node.title))
        return Response({'data': {'id': node._id, 'warning_message': registration_warning, 'links': {'confirm_delete': url}}}, status=status.HTTP_202_ACCEPTED)


class RegistrationCreate(generics.CreateAPIView, RegistrationMixin):
    """
    Save your registration draft
    """
    permission_classes = (
        ContributorOrPublic,
        ReadOnlyIfRegistration,
    )

    serializer_class = RegistrationCreateSerializerWithToken


