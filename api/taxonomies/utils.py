from django.db.models import Count

def optimize_subject_query(subject_queryset):
    """
    Optimize subject queryset for TaxonomySerializer
    """
    return subject_queryset.prefetch_related('parent', 'provider').annotate(children_count=Count('children'))
