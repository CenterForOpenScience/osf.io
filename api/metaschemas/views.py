from rest_framework import generics, permissions as drf_permissions
from api.base.views import DeprecatedView
from framework.auth.oauth_scopes import CoreScopes

from website.project.metadata.schemas import LATEST_SCHEMA_VERSION
from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.base.utils import get_object_or_error

from osf.models import RegistrationSchema
from api.metaschemas.serializers import MetaSchemaSerializer, RegistrationMetaSchemaSerializer


class RegistrationMetaschemaList(JSONAPIBaseView, generics.ListAPIView):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/metaschemas_list).

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_DRAFT_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NODE_DRAFT_REGISTRATIONS_WRITE]

    serializer_class = RegistrationMetaSchemaSerializer
    view_category = 'registration-metaschemas'
    view_name = 'registration-metaschema-list'

    ordering = ('-id',)

    # overrides ListCreateAPIView
    def get_queryset(self):
        return RegistrationSchema.objects.filter(schema_version=LATEST_SCHEMA_VERSION, active=True)


class RegistrationMetaschemaDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/metaschemas_read).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.METASCHEMA_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = RegistrationMetaSchemaSerializer
    view_category = 'registration-metaschemas'
    view_name = 'registration-metaschema-detail'

    # overrides RetrieveAPIView
    def get_object(self):
        schema_id = self.kwargs['metaschema_id']
        return get_object_or_error(RegistrationSchema, schema_id, self.request)


class DeprecatedMetaSchemasList(DeprecatedView, RegistrationMetaschemaList):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/metaschemas_list).
    """
    max_version = '2.7'
    view_category = 'metaschemas'
    view_name = 'metaschema-list'
    serializer_class = MetaSchemaSerializer


class DeprecatedMetaSchemaDetail(DeprecatedView, RegistrationMetaschemaDetail):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/metaschemas_read).
    """
    max_version = '2.7'
    view_category = 'metaschemas'
    view_name = 'metaschema-detail'
    serializer_class = MetaSchemaSerializer
