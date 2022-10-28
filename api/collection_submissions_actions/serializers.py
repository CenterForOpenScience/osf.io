from api.actions.serializers import BaseActionSerializer
from osf.utils.workflows import CollectionSubmissionsTriggers
from api.actions.serializers import TargetRelationshipField
from osf.models import CollectionSubmission
from osf.utils.workflows import ApprovalStates
from api.base.serializers import EnumField


class CollectionSubmissionActionSerializer(BaseActionSerializer):
    class Meta:
        type_ = 'collection-submissions-actions'

    trigger = EnumField(CollectionSubmissionsTriggers)
    from_state = EnumField(ApprovalStates)
    to_state = EnumField(ApprovalStates)

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
