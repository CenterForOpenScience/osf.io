from django.db.models import BooleanField, Case, Count, When

def optimize_subject_query(subject_queryset):
    """
    Optimize subject queryset for TaxonomySerializer
    """
    return subject_queryset.prefetch_related('parent', 'provider').annotate(
        children_count=Count('children'),
        is_other=Case(
            When(text__startswith='Other', then=True),
            default=False,
            output_field=BooleanField(),
        ),
    ).order_by('is_other', 'text')
