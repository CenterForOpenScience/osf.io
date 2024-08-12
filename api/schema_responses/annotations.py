from django.db.models import (
    BooleanField,
    Case,
    Exists,
    OuterRef,
    Subquery,
    When,
    Value,
)
from osf.models import Contributor, Registration, SchemaResponse
from osf.utils.workflows import RegistrationModerationStates


# NOTE: Conveniently assigns None for withdrawn/deleted parents
PARENT_IS_PUBLIC = Subquery(
    Registration.objects.filter(
        id=OuterRef("object_id"),
        deleted__isnull=True,
    )
    .exclude(
        moderation_state=RegistrationModerationStates.WITHDRAWN.db_name,
    )
    .values("is_public")[:1],
    output_field=BooleanField(),
)


IS_ORIGINAL_RESPONSE = Case(
    When(previous_response__isnull=True, then=Value(True)),
    default=Value(False),
    output_field=BooleanField(),
)


def is_pending_current_user_approval(user):
    """Construct a subquery to see if a given user is a pending_approver for a SchemaResponse."""
    return Exists(
        SchemaResponse.pending_approvers.through.objects.filter(
            schemaresponse_id=OuterRef("id"),
            osfuser_id=user.id,
        ),
    )


def user_is_contributor(user):
    """Construct a subquery to determine if user is a contributor to the parent Registration"""
    return Exists(
        Contributor.objects.filter(
            user__id=user.id, node__id=OuterRef("object_id")
        )
    )
