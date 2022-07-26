from django.contrib.contenttypes.models import ContentType
from django.db.models import Exists, OuterRef

from osf.models import OutcomeArtifact
from osf.utils.outcomes import ArtifactTypes


def make_open_practice_badge_annotations():
    registration_ct = ContentType.objects.get_for_model('osf.registration')
    has_data = Exists(
        OutcomeArtifact.objects.select_related('identifier').filter(
            identifier__content_type=registration_ct,
            identifier__object_id=OuterRef('id'),
        ).filter(artifact_type=ArtifactTypes.DATA),
    )
    has_materials = Exists(
        OutcomeArtifact.objects.select_related('identifier').filter(
            identifier__content_type=registration_ct,
            identifier__object_id=OuterRef('id'),
        ).filter(artifact_type=ArtifactTypes.MATERIALS),
    )

    return {'has_data': has_data, 'has_materials': has_materials}
