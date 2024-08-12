from enum import Enum, IntEnum

from django.db.models import CharField, OuterRef, Subquery


class ArtifactTypes(IntEnum):
    """Labels used to classify artifacts.

    Gaps are to allow space for new value to be added later while
    controlling for display order.

    PRIMARY value is arbitrarily large as it is an internal-only concept for now
    """

    UNDEFINED = 0
    DATA = 1
    ANALYTIC_CODE = 11
    MATERIALS = 21
    PAPERS = 31
    SUPPLEMENTS = 41
    PRIMARY = 1001

    @classmethod
    def choices(cls):
        return tuple((entry.value, entry.name) for entry in cls)

    @classmethod
    def public_types(cls):
        return (
            cls.DATA,
            cls.ANALYTIC_CODE,
            cls.MATERIALS,
            cls.PAPERS,
            cls.SUPPLEMENTS,
        )


class OutcomeActions(Enum):
    ADD = 0
    UPDATE = 1
    REMOVE = 2


def make_primary_resource_guid_annotation(base_queryset):
    from osf.models import Guid

    primary_artifacts_and_guids = base_queryset.filter(
        artifact_type=ArtifactTypes.PRIMARY
    ).annotate(
        resource_guid=Subquery(
            Guid.objects.filter(
                content_type=OuterRef("identifier__content_type"),
                object_id=OuterRef("identifier__object_id"),
            )
            .order_by("-created")
            .values("_id")[:1],
            output_field=CharField(),
        )
    )

    return Subquery(
        primary_artifacts_and_guids.filter(
            outcome_id=OuterRef("outcome_id")
        ).values("resource_guid")[:1],
        output_field=CharField(),
    )
