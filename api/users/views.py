from rest_framework import generics, permissions as drf_permissions
from modularodm import Q

from website.models import User
from api.base.utils import get_object_or_404
from api.base.filters import ODMFilterMixin
from .serializers import UserSerializer

class UserList(generics.ListAPIView, ODMFilterMixin):
    """Return a list of registered users."""
    # TODO: Allow unauthenticated requests?
    permission_classes = (
        drf_permissions.IsAuthenticated,
    )
    serializer_class = UserSerializer
    ordering = ('-date_registered')

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        return (
            Q('is_registered', 'eq', True) &
            Q('is_merged', 'ne', True) &
            Q('date_disabled', 'eq', None)
        )

    # overrides ListAPIView
    def get_queryset(self):
        # TODO: sort
        query = self.get_query_from_request()
        return User.find(query)


class UserDetail(generics.RetrieveAPIView):

    serializer_class = UserSerializer

    # overrides RetrieveAPIView
    # TODO: Generalize this?
    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        obj = get_object_or_404(User, self.kwargs[lookup_url_kwarg])
        # May raise a permission denied
        self.check_object_permissions(self.request, obj)
        return obj
