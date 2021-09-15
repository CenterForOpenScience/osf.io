from django.db.models import BooleanField, Exists, OuterRef, Q, Subquery
from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound

from api.base import permissions as base_permissions
from api.base.exceptions import Conflict
from api.base.filters import ListFilterMixin
from api.base.views import JSONAPIBaseView
from api.base.parsers import JSONSchemaParser, JSONAPIParser
from api.nodes.permissions import SchemaResponseDetailPermission, SchemaResponseListPermission
from api.schema_responses.schemas import create_schema_response_payload
from api.schema_responses.serializers import (
    RegistrationSchemaResponseSerializer,
)

from framework.auth.oauth_scopes import CoreScopes

from osf.exceptions import SchemaResponseStateError
from osf.models import Contributor, SchemaResponse, Registration
from osf.utils.workflows import ApprovalStates, RegistrationModerationStates


# Assigns None for deleted and withdrawn Registrations
_is_public_registration_subquery = Subquery(
    Registration.objects.filter(
        id=OuterRef('object_id'), deleted__isnull=True,
    ).exclude(
        moderation_state=RegistrationModerationStates.WITHDRAWN.db_name,
    ).values('is_public')[:1],
    output_field=BooleanField(),
)


def _is_contributor_subquery_for_user(user):
    '''Construct a subquery to determine if user is a contributor to the parent Registration'''
    return Exists(Contributor.objects.filter(user__id=user.id, node__id=OuterRef('object_id')))


def _pending_approval_subquery_for_user(user):
    '''Construct a subquery to see if a given user is a pending_approver for a SchemaResponse.'''
    return Exists(
        SchemaResponse.pending_approvers.through.objects.filter(
            schemaresponse_id=OuterRef('id'), osfuser_id=user.id,
        ),
    )


class SchemaResponseList(JSONAPIBaseView, ListFilterMixin, generics.ListCreateAPIView):
    permission_classes = (
        SchemaResponseListPermission,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.READ_SCHEMA_RESPONSES]
    required_write_scopes = [CoreScopes.WRITE_SCHEMA_RESPONSES]

    parser_classes = (JSONAPIParser, JSONSchemaParser)

    serializer_class = RegistrationSchemaResponseSerializer
    view_category = 'schema_responses'
    view_name = 'schema-responses-list'
    create_payload_schema = create_schema_response_payload

    def get_queryset(self):
        user = self.request.user
        return SchemaResponse.objects.annotate(
            is_contributor=_is_contributor_subquery_for_user(user),
            is_public=_is_public_registration_subquery,
        ).filter(
            # Only surface responses where the user is a contributor
            # and the registration is not withdrawn or deleted
            # or where the registration is public and the response is APPROVED
            (Q(is_contributor=True) & Q(is_public__isnull=False)) |
            (Q(is_public=True) & Q(reviews_state=ApprovalStates.APPROVED.db_name)),
        ).annotate(
            is_pending_current_user_approval=_pending_approval_subquery_for_user(user),
        )

    def get_parser_context(self, http_request):
        """
        Tells parser what json schema we are checking againest.
        """
        res = super().get_parser_context(http_request)
        res['json_schema'] = self.create_payload_schema
        return res


class SchemaResponseDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (
        SchemaResponseDetailPermission,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.READ_SCHEMA_RESPONSES]
    required_write_scopes = [CoreScopes.WRITE_SCHEMA_RESPONSES]

    view_category = 'schema_responses'
    view_name = 'schema-responses-detail'

    def get_serializer_class(self):
        parent = self.get_object().parent

        if isinstance(parent, Registration):
            return RegistrationSchemaResponseSerializer
        else:
            raise NotImplementedError()

    def get_object(self):
        user = self.request.user
        annotated_schema_responses = SchemaResponse.objects.annotate(
            is_public=_is_public_registration_subquery,
            is_pending_current_user_approval=_pending_approval_subquery_for_user(user),
        )

        try:
            response = annotated_schema_responses.get(_id=self.kwargs['schema_response_id'])
        except SchemaResponse.DoesNotExist:
            raise NotFound

        return response

    def perform_destroy(self, instance):
        ## check state
        try:
            instance.delete()
        except SchemaResponseStateError as e:
            raise Conflict(str(e))
