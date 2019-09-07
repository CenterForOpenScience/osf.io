from rest_framework import generics, permissions as drf_permissions
from framework.auth.oauth_scopes import CoreScopes

from api.base.filters import ListFilterMixin
from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView


class EducationList(JSONAPIBaseView, generics.ListCreateAPIView, ListFilterMixin):
    """The documentation for this endpoint is coming soon!
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.EDUCATION_READ]
    required_write_scopes = [CoreScopes.NULL]
    # model_class =

    # serializer_class =
    view_category = 'education'
    view_name = 'education-list'

    ordering = ('-created', )  # default ordering

    def get_default_queryset(self):
        # TODO
        pass

    def get_queryset(self):
        return self.get_queryset_from_request()
