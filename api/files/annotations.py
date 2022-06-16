from django.db.models import BooleanField, Case, Exists, F, IntegerField, Max, OuterRef, Q, Subquery, Value, When
from django.db.models.functions.base import Cast
from django.contrib.postgres.fields.jsonb import KeyTextTransform
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import NonNaiveDateTimeField
from osf.models import FileVersion


# Get date modified for OSF and non-OSF providers
DATE_MODIFIED = Case(
    When(
        provider='osfstorage',
        then=Cast(Max('versions__created'), NonNaiveDateTimeField()),
    ),
    default=Cast(
        KeyTextTransform(
            'value',
            Cast(
                KeyTextTransform(
                    'modified',
                    Cast(
                        KeyTextTransform(
                            -1,
                            '_history',
                        ), output_field=DateTimeAwareJSONField(),
                    ),
                ), output_field=DateTimeAwareJSONField(),
            ),
        ), output_field=NonNaiveDateTimeField(),
    ),
)

def make_current_user_has_viewed_annotations(user):
    '''Returns the set of annotations required to set the current_user_has_viewed attribute.'''
    seen_versions = FileVersion.objects.annotate(
        latest_version=Subquery(
            FileVersion.objects.filter(
                basefilenode=OuterRef('basefilenode'),
            ).order_by('-created').values('id')[:1],
            output_field=IntegerField(),
        ),
    ).filter(seen_by=user)

    has_seen_latest = Exists(
        seen_versions.filter(basefilenode=OuterRef('id').filter(id=F('latest_version'))),
    )
    has_previously_seen = Exists(
        seen_versions.filter(basefilenode=OuterRef('id').exclude(id=F('latest_version'))),
    )
    current_user_has_viewed = Case(
        When(Q(latest_seen=True) | Q(previously_seen=False), then=Value(True)),
        default=Value(False),
        output_field=BooleanField(),
    )

    return {
        'has_seen_latest': has_seen_latest,
        'has_previously_seen': has_previously_seen,
        'current_user_has_viewed': current_user_has_viewed,
    }
