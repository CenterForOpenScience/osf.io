from rest_framework.filters import OrderingFilter


class ODMOrderingFilter(OrderingFilter):
    """Adaptation of rest_framework.filters.OrderingFilter to work with modular-odm."""

    # override
    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)
        if ordering:
            return queryset.sort(*ordering)
        return queryset
