from django.db.models import F, Case, When, IntegerField

from website import settings


STORAGE_USAGE_QUERY = {
    'public_cap': Case(
        When(
            custom_storage_usage_limit_public=None,
            then=settings.STORAGE_LIMIT_PUBLIC,
        ),
        When(
            custom_storage_usage_limit_public__gt=0,
            then=F('custom_storage_usage_limit_public'),
        ),
        output_field=IntegerField()
    ),
    'private_cap': Case(
        When(
            custom_storage_usage_limit_private=None,
            then=settings.STORAGE_LIMIT_PRIVATE,
        ),
        When(
            custom_storage_usage_limit_private__gt=0,
            then=F('custom_storage_usage_limit_private'),
        ),
        output_field=IntegerField()
    )
}
