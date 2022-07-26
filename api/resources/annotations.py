from django.contrib.contenttypes.models import ContentType
from django.db.models import Exists, OuterRef

from osf.models import OutcomeArtifact
from osf.utils.outcomes import ArtifactTypes

def _make_badge_subquery(primary_resource_ct, artifact_type):
    return Exists(
        OutcomeArtifact.objects.select_related('identifier').filter(
            identifier__content_type=primary_resource_ct,
            identifier__object_id=OuterRef('id'),
            finalized=True,
            deleted__isnull=False,
            artifact_type=artifact_type,
        ),
    )


def make_open_practice_badge_annotations():
    registration_ct = ContentType.objects.get_for_model('osf.registration')
    return {
        'has_data': _make_badge_subquery(registration_ct, ArtifactTypes.DATA),
        'has_analytic_code': _make_badge_subquery(registration_ct, ArtifactTypes.CODE),
        'has_materials': _make_badge_subquery(registration_ct, ArtifactTypes.MATERIALS),
    }
