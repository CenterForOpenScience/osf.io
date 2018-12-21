from rest_framework.permissions import IsAuthenticatedOrReadOnly

class IsAuthenticatedOrReadOnlyForSearch(IsAuthenticatedOrReadOnly):
    def has_permission(self, request, view):
        from api.search.views import BaseSearchView
        if not isinstance(view, BaseSearchView):
            return False
        return request.method == 'POST' or super(IsAuthenticatedOrReadOnlyForSearch, self).has_permission(request, view)
