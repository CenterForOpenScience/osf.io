from django.db.models import Q
from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound

from api.actions.serializers import SchemaResponseActionSerializer
from api.base import permissions as base_permissions
from api.base.exceptions import Conflict
from api.base.filters import ListFilterMixin
from api.base.parsers import (
    JSONSchemaParser,
    JSONAPIParser,
    JSONAPIMultipleRelationshipsParser,
    JSONAPIMultipleRelationshipsParserForRegularJSON,
)
from api.base.utils import get_object_or_error
from api.base.views import JSONAPIBaseView
from api.schema_responses import annotations
from api.schema_responses.permissions import (
    SchemaResponseDetailPermission,
    SchemaResponseListPermission,
    SchemaResponseActionDetailPermission,
    SchemaResponseActionListPermission,
)
from api.schema_responses.schemas import create_schema_response_payload
from api.schema_responses.serializers import (
    RegistrationSchemaResponseSerializer,
)

from framework.auth.oauth_scopes import CoreScopes

from osf.exceptions import SchemaResponseStateError
from osf.models import SchemaResponse, SchemaResponseAction
from osf.utils.workflows import ApprovalStates


class SchemaResponseList(
    JSONAPIBaseView,
    ListFilterMixin,
    generics.ListCreateAPIView,
):
    permission_classes = (
        SchemaResponseListPermission,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.READ_SCHEMA_RESPONSES]
    required_write_scopes = [CoreScopes.WRITE_SCHEMA_RESPONSES]

    parser_classes = (JSONAPIParser, JSONSchemaParser)

    serializer_class = RegistrationSchemaResponseSerializer
    view_category = "schema_responses"
    view_name = "schema-responses-list"
    create_payload_schema = create_schema_response_payload

    def get_queryset(self):
        """Retrieve the list of SchemaResponses visible to the user.

        This should be the union of all APPROVED SchemaResponses on Public registrations
        and all SchemaResponses for registrations on which the caller is a contributor
        (excluding any SchemaResponses on WITHDRAWN or deleted registrations).
        """
        user = self.request.user
        return (
            SchemaResponse.objects.annotate(
                user_is_contributor=annotations.user_is_contributor(user),
                parent_is_public=annotations.PARENT_IS_PUBLIC,
            )
            .exclude(
                Q(
                    parent_is_public__isnull=True,
                ),  # Withdrawn or deleted parent, always exclude
            )
            .filter(
                Q(user_is_contributor=True)
                | (
                    Q(parent_is_public=True)
                    & Q(reviews_state=ApprovalStates.APPROVED.db_name)
                ),
            )
            .annotate(
                is_pending_current_user_approval=annotations.is_pending_current_user_approval(
                    user,
                ),
                is_original_response=annotations.IS_ORIGINAL_RESPONSE,
            )
        )

    def get_parser_context(self, http_request):
        """
        Tells parser what json schema we are checking againest.
        """
        res = super().get_parser_context(http_request)
        res["json_schema"] = self.create_payload_schema
        return res


class SchemaResponseDetail(
    JSONAPIBaseView,
    generics.RetrieveUpdateDestroyAPIView,
):
    permission_classes = (
        SchemaResponseDetailPermission,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.READ_SCHEMA_RESPONSES]
    required_write_scopes = [CoreScopes.WRITE_SCHEMA_RESPONSES]

    view_category = "schema_responses"
    view_name = "schema-responses-detail"

    serializer_class = RegistrationSchemaResponseSerializer

    def get_object(self):
        user = self.request.user
        annotated_schema_response = SchemaResponse.objects.filter(
            _id=self.kwargs["schema_response_id"],
        ).annotate(
            is_pending_current_user_approval=annotations.is_pending_current_user_approval(
                user,
            ),
            is_original_response=annotations.IS_ORIGINAL_RESPONSE,
        )

        try:
            return annotated_schema_response.get()
        except SchemaResponse.DoesNotExist:
            raise NotFound

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except SchemaResponseStateError as e:
            raise Conflict(str(e))


class SchemaResponseActionList(
    JSONAPIBaseView,
    ListFilterMixin,
    generics.ListCreateAPIView,
):
    permission_classes = (
        SchemaResponseActionListPermission,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.READ_SCHEMA_RESPONSES]
    required_write_scopes = [CoreScopes.WRITE_SCHEMA_RESPONSES]

    parser_classes = (
        JSONAPIMultipleRelationshipsParser,
        JSONAPIMultipleRelationshipsParserForRegularJSON,
    )

    view_category = "schema_responses"
    view_name = "schema-response-action-list"
    serializer_class = SchemaResponseActionSerializer

    def get_queryset(self):
        return self.get_object().actions.all().order_by("created")

    def get_object(self):
        return get_object_or_error(
            model_or_qs=SchemaResponse,
            query_or_pk=self.kwargs["schema_response_id"],
            request=self.request,
            check_deleted=False,
        )


class SchemaResponseActionDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    permission_classes = (
        SchemaResponseActionDetailPermission,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.READ_SCHEMA_RESPONSES]
    required_write_scopes = [CoreScopes.WRITE_SCHEMA_RESPONSES]

    view_category = "schema_responses"
    view_name = "schema-responses-detail"

    serializer_class = SchemaResponseActionSerializer

    def get_object(self):
        return get_object_or_error(
            SchemaResponseAction,
            query_or_pk=self.kwargs["schema_response_action_id"],
            request=self.request,
        )
