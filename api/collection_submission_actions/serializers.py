from api.base.utils import absolute_reverse

from api.base.serializers import EnumField
from api.actions.serializers import TargetRelationshipField
from osf.models import CollectionSubmission
from osf.utils.workflows import (
    CollectionSubmissionStates,
    CollectionSubmissionsTriggers,
)
from rest_framework import serializers as ser
from api.base.serializers import (
    JSONAPISerializer,
    LinksField,
    VersionedDateTimeField,
)

from api.base.serializers import (
    RelationshipField,
)
from api.base.exceptions import JSONAPIAttributeException
from django.core.exceptions import PermissionDenied
from transitions import MachineError
from framework.exceptions import PermissionsError
from api.base.exceptions import Conflict
from django.core.exceptions import ValidationError


class CollectionSubmissionActionSerializer(JSONAPISerializer):
    class Meta:
        type_ = "collection-submission-actions"

    id = ser.CharField(source="_id", read_only=True)

    trigger = EnumField(CollectionSubmissionsTriggers)
    from_state = EnumField(CollectionSubmissionStates, required=False)
    to_state = EnumField(CollectionSubmissionStates, required=False)
    comment = ser.CharField(
        max_length=65535, required=False, allow_blank=True, allow_null=True
    )
    date_created = VersionedDateTimeField(source="created", read_only=True)
    date_modified = VersionedDateTimeField(source="modified", read_only=True)

    collection = RelationshipField(
        related_view="collections:collection-detail",
        related_view_kwargs={"collection_id": "<target.collection._id>"},
    )

    creator = RelationshipField(
        read_only=True,
        related_view="users:user-detail",
        related_view_kwargs={"user_id": "<creator._id>"},
    )

    target = TargetRelationshipField(
        target_class=CollectionSubmission,
        read_only=False,
        required=True,
        related_view="collections:collection-submission-detail",
        related_view_kwargs={
            "collection_id": "<target.collection._id>",
            "collection_submission_id": "<target.guid._id>",
        },
        filter_key="target__guids___id",
    )

    links = LinksField(
        {
            "self": "get_action_url",
        },
    )

    def get_absolute_url(self, obj):
        return self.get_action_url(obj)

    def get_action_url(self, obj):
        return absolute_reverse(
            "actions:action-detail",
            kwargs={
                "action_id": obj._id,
                "version": self.context["request"].parser_context["kwargs"][
                    "version"
                ],
            },
        )

    def create(self, validated_data):
        user = self.context["request"].user
        trigger = CollectionSubmissionsTriggers(validated_data.get("trigger"))
        collection_submission = validated_data.pop("target")
        comment = validated_data.pop("comment", "")
        try:
            if trigger == CollectionSubmissionsTriggers.SUBMIT:
                collection_submission.submit(user=user, comment=comment)
            elif trigger == CollectionSubmissionsTriggers.ACCEPT:
                collection_submission.accept(user=user, comment=comment)
            elif trigger == CollectionSubmissionsTriggers.REJECT:
                collection_submission.reject(user=user, comment=comment)
            elif trigger == CollectionSubmissionsTriggers.REMOVE:
                collection_submission.remove(user=user, comment=comment)
            elif trigger == CollectionSubmissionsTriggers.RESUBMIT:
                collection_submission.resubmit(user=user, comment=comment)
            elif trigger == CollectionSubmissionsTriggers.CANCEL:
                collection_submission.cancel(user=user, comment=comment)
            else:
                raise JSONAPIAttributeException(
                    attribute="trigger", detail="Invalid trigger."
                )
        except PermissionsError as exc:
            raise PermissionDenied(exc)
        except MachineError:
            raise Conflict(
                f'Trigger "{trigger.db_name}" is not supported for the target CollectionSubmission '
                f'with id [{collection_submission._id}] in state "{collection_submission.state.db_name}"',
            )
        except ValueError as exc:
            raise ValidationError(exc)
        return collection_submission.actions.last()
