from django.db.models import Max, Case, When, DateTimeField
from django.db.models.functions.base import Cast
from django.contrib.postgres.fields.jsonb import KeyTextTransform, JSONField


# Get date modified for OSF and non-OSF providers
DATE_MODIFIED = Case(
    When(
        provider='osfstorage',
        then=Cast(Max('versions__created'), DateTimeField()),
    ),
    default=Cast(
        KeyTextTransform(
            'modified',
            Cast(
                KeyTextTransform(-1, '_history'),
                output_field=JSONField(),
            ),
        ),
        output_field=DateTimeField(),
    ),
)
