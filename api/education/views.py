from rest_framework import generics, permissions as drf_permissions
from framework.auth.oauth_scopes import CoreScopes

from osf.models import Education
from api.base.filters import ListFilterMixin
from api.base import permissions as base_permissions
from api.base.utils import get_object_or_error
from api.users.permissions import ReadOnlyOrCurrentUser
from api.education.serializers import EducationSerializer, EducationDetailSerializer
from api.base.views import JSONAPIBaseView


class EducationDetail(JSONAPIBaseView, generics.RetrieveUpdateAPIView):
    """The documentation for this endpoint is coming soon!
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        base_permissions.PermissionWithGetter(ReadOnlyOrCurrentUser, 'user'),
    )

    required_read_scopes = [CoreScopes.EDUCATION_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = EducationSerializer
    view_category = 'education'
    view_name = 'education-detail'
    lookup_url_kwarg = 'education_id'

    def get_serializer_class(self):
        """
        Use EducationDetailSerializer which requires 'id' and does not require institution
        """
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return EducationDetailSerializer
        else:
            return EducationSerializer

    # overrides RetrieveAPIView
    def get_object(self):
        education_entry = get_object_or_error(
            Education,
            self.kwargs[self.lookup_url_kwarg],
            self.request,
            display_name='education',
        )
        self.check_object_permissions(self.request, education_entry)
        return education_entry


class EducationList(JSONAPIBaseView, generics.ListCreateAPIView, ListFilterMixin):
    """The documentation for this endpoint is coming soon!
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        base_permissions.PermissionWithGetter(ReadOnlyOrCurrentUser, 'user'),
    )

    required_read_scopes = [CoreScopes.EDUCATION_READ]
    required_write_scopes = [CoreScopes.NULL]
    model_class = Education

    serializer_class = EducationSerializer
    view_category = 'education'
    view_name = 'education-list'

    ordering = ('-created', )  # default ordering

    def get_default_queryset(self):
        return Education.objects.all()

    def get_queryset(self):
        return self.get_queryset_from_request()
