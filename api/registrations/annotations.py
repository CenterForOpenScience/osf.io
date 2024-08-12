from django.db.models import CharField, OuterRef, Subquery
from osf.models import SchemaResponse

REVISION_STATE = Subquery(
    SchemaResponse.objects.filter(
        nodes__id=OuterRef("root_id"),
    )
    .order_by("-created")
    .values("reviews_state")[:1],
    output_field=CharField(),
)
