import waffle
from rest_framework import generics, permissions as drf_permissions
from framework.auth.oauth_scopes import CoreScopes

from website.project.metadata.schemas import LATEST_SCHEMA_VERSION
from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.base.utils import get_object_or_error
from api.base.filters import ListFilterMixin

from osf.models import RegistrationSchema
from osf.features import ENABLE_INACTIVE_SCHEMAS
from api.schemas.serializers import RegistrationSchemaSerializer


class RegistrationSchemaList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/metaschemas_list).

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_DRAFT_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NODE_DRAFT_REGISTRATIONS_WRITE]

    serializer_class = RegistrationSchemaSerializer
    view_category = 'registration-schemas'
    view_name = 'registration-schema-list'

    ordering = ('-id',)

    def get_default_queryset(self):
        if waffle.switch_is_active(ENABLE_INACTIVE_SCHEMAS):
            return RegistrationSchema.objects.filter(schema_version=LATEST_SCHEMA_VERSION, visible=True)
        else:
            return RegistrationSchema.objects.filter(schema_version=LATEST_SCHEMA_VERSION, active=True, visible=True)

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()


class RegistrationSchemaDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/metaschemas_read).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.SCHEMA_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = RegistrationSchemaSerializer
    view_category = 'registration-schemas'
    view_name = 'registration-schema-detail'

    # overrides RetrieveAPIView
    def get_object(self):
        schema_id = self.kwargs['schema_id']
        return get_object_or_error(RegistrationSchema, schema_id, self.request)
