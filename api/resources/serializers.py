from django.db import IntegrityError
from rest_framework import serializers as ser

from api.base.exceptions import Conflict, JSONAPIException
from api.base.serializers import (
    EnumField,
    JSONAPISerializer,
    LinksField,
    RelationshipField,
    TypeField,
    VersionedDateTimeField,
)
from api.base.utils import absolute_reverse
from osf.exceptions import (
    CannotFinalizeArtifactError,
    InvalidPIDError,
    NoPIDError,
    UnsupportedArtifactTypeError,
)
from osf.models import Outcome, OutcomeArtifact, Registration
from osf.utils.outcomes import ArtifactTypes


MODEL_TO_SERIALIZER_FIELD_MAPPINGS = {
    "artifact_type": "resource_type",
    "identifier__value": "pid",
}


class ResourceSerializer(JSONAPISerializer):
    filterable_fields = frozenset(
        [
            "date_created",
            "date_modified",
            "resource_type",
        ]
    )

    non_anonymized_fields = frozenset(
        [
            "id",
            "type",
            "date_created",
            "date_modified",
            "description",
            "links",
            "registration",
            "resource_type",
        ]
    )

    class Meta:
        type_ = "resources"

    id = ser.CharField(source="_id", read_only=True, required=False)
    type = TypeField()

    date_created = VersionedDateTimeField(source="created", required=False)
    date_modified = VersionedDateTimeField(source="modified", required=False)

    description = ser.CharField(
        allow_null=False, allow_blank=True, required=False
    )
    resource_type = EnumField(
        ArtifactTypes, source="artifact_type", allow_null=False, required=False
    )
    finalized = ser.BooleanField(required=False)

    # Reference to obj.identifier.value, populated via annotation on default manager
    pid = ser.CharField(allow_null=False, allow_blank=True, required=False)

    # primary_resource_guid is populated via annotation on the default manager
    registration = RelationshipField(
        related_view="registrations:registration-detail",
        related_view_kwargs={"node_id": "<primary_resource_guid>"},
        read_only=True,
        required=False,
        allow_null=True,
    )

    links = LinksField({"self": "get_absolute_url"})

    def get_absolute_url(self, obj):
        return absolute_reverse(
            "resources:resource-detail",
            kwargs={
                "version": self.context["request"].parser_context["kwargs"][
                    "version"
                ],
                "resource_id": obj._id,
            },
        )

    def create(self, validated_data):
        # Already loaded by view, so no need to error check
        guid = self.context["request"].data["registration"]
        primary_registration = Registration.load(guid)

        try:
            root_outcome = Outcome.objects.for_registration(
                primary_registration, create=True
            )
        except NoPIDError:
            raise Conflict(
                "Cannot add Resources to a Registration that does not have a DOI"
            )

        return OutcomeArtifact.objects.create(outcome=root_outcome)

    def update(self, instance, validated_data):
        updated_description = validated_data.get("description")
        if updated_description == instance.description:
            updated_description = None

        updated_artifact_type = validated_data.get("artifact_type")
        if updated_artifact_type == instance.artifact_type:
            updated_artifact_type = None

        updated_pid_value = validated_data.get("pid")
        if updated_pid_value == instance.pid:
            updated_pid_value = None

        try:
            instance.update(
                new_description=updated_description,
                new_artifact_type=updated_artifact_type,
                new_pid_value=updated_pid_value,
                api_request=self.context["request"],
            )
        except UnsupportedArtifactTypeError:
            current_type = ArtifactTypes(instance.artifact_type).name.lower()
            raise JSONAPIException(
                detail=(
                    f"Error updating resource_type for Resource with id [{instance._id}]: "
                    f'currently has a resource_type of "{current_type}", cannot return '
                    'resource_type to "undefined".'
                ),
                source={"pointer": "/data/attributes/resource_type"},
            )
        except InvalidPIDError as e:
            raise JSONAPIException(
                detail=f"Error updating PID for Resource with id [{instance._id}]: {e.message}",
                source={"pointer": "/data/attributes/pid"},
            )
        except IntegrityError:
            raise JSONAPIException(
                detail="A Resource with the provided PID and Resource Type already exists.",
                source={"pointer": "/data/attributes"},
            )

        finalized = validated_data.get("finalized")
        if finalized is not None:
            self._update_finalized(instance, finalized)

        instance.save()
        instance.pid = instance.identifier.value
        return instance

    def _update_finalized(self, instance, patched_finalized):
        # No change -> noop
        if instance.finalized == patched_finalized:
            return

        # Previous check alerts us that patched_finalized is False here
        if instance.finalized:
            raise Conflict(
                detail=(
                    "Resource with id [{instance._id}] has state `finalized: true`, "
                    "cannot PATCH `finalized: false"
                ),
                source={"pointer": "/data/attributes/finalized"},
            )

        try:
            instance.finalize(api_request=self.context["request"])
        except CannotFinalizeArtifactError as e:
            error_sources = [
                MODEL_TO_SERIALIZER_FIELD_MAPPINGS[field]
                for field in e.incomplete_fields
            ]
        except IntegrityError:
            raise JSONAPIException(
                detail="A Resource with the provided PID and Resource Type already exists.",
                source={"pointer": "/data/attributes"},
            )
        else:
            return

        source = "/data/attributes/"
        if len(error_sources) == 1:  # Be more specific if possible
            source += error_sources[0]

        raise Conflict(
            detail=(
                f"Cannot PATCH `finalized: true` for Resource with id [{instance._id}] "
                f"until the following required fields are populated {error_sources}."
            ),
            source={"pointer": source},
        )

        return True
