from django.db.models import Max, Case, When, DateTimeField
from django.db.models.functions.base import Cast
from django.contrib.postgres.fields.jsonb import KeyTextTransform, JSONField
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import NonNaiveDateTimeField
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONFormField


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
                            '_history'
                        ), output_field=DateTimeAwareJSONField()
                    )
                ), output_field=DateTimeAwareJSONField()
            )
        ), output_field=NonNaiveDateTimeField()
    )
)
