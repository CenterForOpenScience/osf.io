from framework.exceptions import PermissionsError
from api.actions.serializers import BaseActionSerializer
from osf.utils import permissions
from osf.utils.workflows import CollectionSubmissionsTriggers
from rest_framework import serializers as ser
from rest_framework.exceptions import PermissionDenied, ValidationError
from transitions import MachineError
from api.actions.serializers import TargetRelationshipField
from api.base.exceptions import Conflict
from api.base.exceptions import JSONAPIAttributeException
from osf.models import CollectionSubmission


class CollectionSubmissionActionSerializer(BaseActionSerializer):
    class Meta:
        type_ = 'collection-submissions-actions'

    permissions = ser.ChoiceField(choices=permissions.API_CONTRIBUTOR_PERMISSIONS, required=False)
    visible = ser.BooleanField(default=True, required=False)
    trigger = ser.ChoiceField(choices=CollectionSubmissionsTriggers.char_field_choices())

    target = TargetRelationshipField(
        target_class=CollectionSubmission,
        read_only=False,
        required=True,
        related_view='collection_submissions:collection-submissions-detail',
        related_view_kwargs={
            'collection_id': '<target.guid._id>',
            'cgm_id': '<self._id>',
        },
        filter_key='target__guid___id',
    )

    def create(self, validated_data):
        user = self.context['request'].user
        trigger = validated_data.get('trigger')
        collection_submission = validated_data.pop('target')
        comment = validated_data.pop('comment', '')
        previous_action = collection_submission.actions.last()
        old_state = collection_submission.reviews_state
        try:
            if trigger == CollectionSubmissionsTriggers.SUBMIT.db_name:
                collection_submission.submit(user=user, comment=comment)
            elif trigger == CollectionSubmissionsTriggers.APPROVE.db_name:
                collection_submission.approve(user=user, comment=comment)
            elif trigger == CollectionSubmissionsTriggers.ADMIN_REMOVE.db_name:
                collection_submission.reject(user=user, comment=comment)
            elif trigger == CollectionSubmissionsTriggers.MODERATOR_REMOVE.db_name:
                collection_submission.reject(user=user, comment=comment)
            else:
                raise JSONAPIAttributeException(attribute='trigger', detail='Invalid trigger.')
        except PermissionsError as exc:
            raise PermissionDenied(exc)
        except MachineError:
            raise Conflict(
                f'Trigger "{trigger}" is not supported for the target CollectionSubmission '
                f'with id [{collection_submission._id}] in state "{collection_submission.reviews_state}"',
            )
        except ValueError as exc:
            raise ValidationError(exc)

        new_action = collection_submission.actions.last()
        if new_action is None or new_action == previous_action or new_action.trigger != trigger:
            print("DIDn't advance state")
            raise Conflict(
                f'Trigger "{trigger}" is not supported for the target CollectionSubmission '
                f'with id [{collection_submission._id}] in state "{old_state}"',
            )

        return collection_submission.actions.last()
