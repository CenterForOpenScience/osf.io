from api.actions.serializers import BaseActionSerializer
from osf.utils import permissions
from osf.utils.workflows import CollectionSubmissionsTriggers
from rest_framework import serializers as ser
from api.actions.serializers import TargetRelationshipField
from osf.models import CollectionSubmission
from osf.utils.workflows import ApprovalStates


class CollectionSubmissionActionSerializer(BaseActionSerializer):
    class Meta:
        type_ = 'collection-submissions-actions'

    permissions = ser.ChoiceField(choices=permissions.API_CONTRIBUTOR_PROVIDER_PERMISSIONS, required=False)
    visible = ser.BooleanField(default=True, required=False)
    trigger = ser.ChoiceField(choices=CollectionSubmissionsTriggers.char_field_choices())
    from_state = ser.ChoiceField(choices=ApprovalStates.char_field_choices(), read_only=True)
    to_state = ser.ChoiceField(choices=ApprovalStates.char_field_choices(), read_only=True)

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
