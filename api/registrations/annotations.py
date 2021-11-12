from django.db.models import CharField, OuterRef, Subquery
from osf.models import SchemaResponse
from osf.utils.workflows import ApprovalStates

REVISION_STATE = Subquery(
    SchemaResponse.objects.filter(
        nodes__id=OuterRef('id'),
    ).order_by('-created').values('reviews_state')[:1],
    output_field=CharField(),
)

LATEST_RESPONSE_ID = Subquery(
    SchemaResponse.objects.filter(
        nodes__id=OuterRef('id'), reviews_state=ApprovalStates.APPROVED.db_name,
    ).order_by('-created').values('_id')[:1],
    output_field=CharField(),
)

ORIGINAL_RESPONSE_ID = Subquery(
    SchemaResponse.objects.filter(
        nodes__id=OuterRef('id'),
    ).order_by('created').values('_id')[:1],
    output_field=CharField(),
)
