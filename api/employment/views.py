from rest_framework import generics, permissions as drf_permissions
from framework.auth.oauth_scopes import CoreScopes

from osf.models import Employment
from api.base.filters import ListFilterMixin
from api.base import permissions as base_permissions
from api.base.utils import get_object_or_error
from api.employment.serializers import EmploymentSerializer
from api.base.views import JSONAPIBaseView


class EmploymentDetail(JSONAPIBaseView, generics.RetrieveUpdateAPIView):
    """The documentation for this endpoint is coming soon!
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        base_permissions.CurrentUserOrReadOnly,
    )

    required_read_scopes = [CoreScopes.EMPLOYMENT_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = EmploymentSerializer
    view_category = 'employment'
    view_name = 'employment-detail'
    lookup_url_kwarg = 'education_id'

    # overrides RetrieveAPIView
    def get_object(self):
        education_entry = get_object_or_error(
            Employment,
            self.kwargs[self.lookup_url_kwarg],
            self.request,
            display_name='employment',
        )
        self.check_object_permissions(self.request, education_entry)
        return education_entry


class EmploymentList(JSONAPIBaseView, generics.ListCreateAPIView, ListFilterMixin):
    """The documentation for this endpoint is coming soon!
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        base_permissions.CurrentUserOrReadOnly,
    )

    required_read_scopes = [CoreScopes.EDUCATION_READ]
    required_write_scopes = [CoreScopes.NULL]
    model_class = Employment

    serializer_class = EmploymentSerializer
    view_category = 'employment'
    view_name = 'employment-list'

    ordering = ('-created', )  # default ordering

    def get_default_queryset(self):
        return Employment.objects.all()

    def get_queryset(self):
        return self.get_queryset_from_request()
