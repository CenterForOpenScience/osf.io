from api.base.exceptions import Conflict
from api.base.serializers import JSONAPISerializer, LinksField, TypeField
from api.base.utils import absolute_reverse, get_object_or_error
from rest_framework import serializers as ser
from rest_framework.exceptions import ValidationError

from api.base.serializers import (
    RelationshipField,
    VersionedDateTimeField,
)

from osf.exceptions import (
    PreviousSchemaResponseError,
    SchemaResponseStateError,
    SchemaResponseUpdateError,
)
from osf.models import (
    Registration,
    SchemaResponse,
)
from osf.utils.workflows import ApprovalStates


class RegistrationSchemaResponseSerializer(JSONAPISerializer):
    filterable_fields = frozenset(
        [
            "date_created",
            "date_modified",
            "revision_justification",
            "reviews_state",
        ],
    )
    writeable_method_fields = frozenset(
        [
            "revision_responses",
        ],
    )

    non_anonymized_fields = frozenset(
        [
            "id",
            "date_created",
            "date_modified",
            "date_submitted",
            "is_original_response",
            "links",
            "registration",
            "registration_schema",
            "revision_justification",
            "revision_responses",
            "updated_response_keys",
        ],
    )

    id = ser.CharField(source="_id", required=True, allow_null=True)
    type = TypeField()
    date_created = VersionedDateTimeField(source="created", required=False)
    date_submitted = VersionedDateTimeField(
        source="submitted_timestamp",
        required=False,
    )
    date_modified = VersionedDateTimeField(source="modified", required=False)
    revision_justification = ser.CharField(required=False, allow_blank=True)
    revision_responses = ser.JSONField(source="all_responses", required=False)
    updated_response_keys = ser.JSONField(required=False, read_only=True)
    reviews_state = ser.CharField(required=False)
    # Populated via annotation on relevant API views
    is_pending_current_user_approval = ser.BooleanField(required=False)
    is_original_response = ser.BooleanField(required=False)

    links = LinksField(
        {
            "self": "get_absolute_url",
        },
    )

    actions = RelationshipField(
        related_view="schema_responses:schema-response-action-list",
        related_view_kwargs={"schema_response_id": "<_id>"},
        read_only=True,
        required=False,
    )

    registration = RelationshipField(
        related_view="registrations:registration-detail",
        related_view_kwargs={"node_id": "<parent._id>"},
        read_only=True,
        required=False,
    )

    registration_schema = RelationshipField(
        related_view="schemas:registration-schema-detail",
        related_view_kwargs={"schema_id": "<schema._id>"},
        read_only=True,
        required=False,
    )

    initiated_by = RelationshipField(
        related_view="users:user-detail",
        related_view_kwargs={"user_id": "<initiator._id>"},
        read_only=True,
        required=False,
    )

    class Meta:
        type_ = "schema-responses"

    def get_absolute_url(self, obj):
        return absolute_reverse(
            "schema_responses:schema-responses-detail",
            kwargs={
                "version": self.context["request"].parser_context["kwargs"][
                    "version"
                ],
                "schema_response_id": obj._id,
            },
        )

    def create(self, validated_data):
        try:
            registration_id = validated_data.pop("_id")
        except KeyError:
            raise ValidationError("payload must contain valid Registration id")

        registration = get_object_or_error(
            Registration,
            query_or_pk=registration_id,
            request=self.context["request"],
        )
        if not registration.updatable:
            raise Conflict(
                detail=f"Registration with guid {registration._id} cannot be updated.",
            )

        initiator = self.context["request"].user
        justification = validated_data.pop("revision_justification", "")

        latest_response = registration.schema_responses.first()
        if not latest_response:
            try:
                return SchemaResponse.create_initial_response(
                    parent=registration,
                    initiator=initiator,
                    justification=justification,
                )
            # Value Error when no schema provided
            except ValueError:
                raise ValidationError(
                    f"Resource {registration._id} must specify a schema",
                )

        try:
            return SchemaResponse.create_from_previous_response(
                initiator=initiator,
                previous_response=latest_response,
                justification=justification,
            )
        except PreviousSchemaResponseError as exc:
            raise Conflict(detail=str(exc))

    def update(self, schema_response, validated_data):
        if schema_response.state is not ApprovalStates.IN_PROGRESS:
            raise Conflict(
                detail=(
                    f"SchemaResponse has state `{schema_response.reviews_state}` "
                    f"state must be {ApprovalStates.IN_PROGRESS.db_name}",
                ),
            )

        revision_responses = validated_data.get("revision_responses")
        justification = validated_data.get("revision_justification")

        if justification:
            schema_response.revision_justification = justification

        if revision_responses:
            try:
                schema_response.update_responses(revision_responses)
            except SchemaResponseUpdateError as exc:
                raise ValidationError(detail=str(exc))
            except SchemaResponseStateError as exc:
                # should have been handled above, but catch again just in case
                raise Conflict(detail=str(exc))

        schema_response.save()
        return schema_response
