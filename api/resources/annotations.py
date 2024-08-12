from django.contrib.contenttypes.models import ContentType
from django.db.models import Exists, IntegerField, OuterRef, Subquery

from osf.models import OutcomeArtifact, Registration
from osf.utils.outcomes import ArtifactTypes


def _make_badge_subquery(artifact_type):
    """Make the subquery for a specific Open Practice Badge.

    Requires `primary_outcome_id` annotation be present. As such, this should only be called
    from make_open_practice_badge_annotations.
    """
    return Exists(
        OutcomeArtifact.objects.filter(
            outcome_id=OuterRef("primary_outcome_id"),
            finalized=True,
            deleted__isnull=True,
            artifact_type=artifact_type,
        ),
    )


def make_open_practice_badge_annotations():
    """Builds all of the annotation Subqueries for OpenPractice badges."""
    # TODO: Accept CT as a param if/when PRIMARY artifact can be something other than a Registration
    primary_resource_ct = ContentType.objects.get_for_model(Registration)
    primary_outcome_subquery = Subquery(
        OutcomeArtifact.objects.filter(
            artifact_type=ArtifactTypes.PRIMARY,
            identifier__content_type=primary_resource_ct,
            identifier__object_id=OuterRef("id"),
        ).values("outcome_id")[:1],
        output_field=IntegerField(),
    )

    return {
        "primary_outcome_id": primary_outcome_subquery,
        "has_data": _make_badge_subquery(ArtifactTypes.DATA),
        "has_analytic_code": _make_badge_subquery(ArtifactTypes.ANALYTIC_CODE),
        "has_materials": _make_badge_subquery(ArtifactTypes.MATERIALS),
        "has_papers": _make_badge_subquery(ArtifactTypes.PAPERS),
        "has_supplements": _make_badge_subquery(ArtifactTypes.SUPPLEMENTS),
    }
