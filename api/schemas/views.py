import waffle
from rest_framework import exceptions, generics, permissions as drf_permissions
from framework.auth.oauth_scopes import CoreScopes

from website.project.metadata.schemas import LATEST_SCHEMA_VERSION
from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.base.utils import get_object_or_error
from api.base.filters import ListFilterMixin

from osf.features import ENABLE_INACTIVE_SCHEMAS
from osf.models import RegistrationFormBlock, RegistrationSchema
from api.schemas.serializers import (
    RegistrationSchemaSerializer,
    RegistrationSchemaFormBlockSerializer,
)


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
    view_category = 'schemas'
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
    view_category = 'schemas'
    view_name = 'registration-schema-detail'

    # overrides RetrieveAPIView
    def get_object(self):
        schema_id = self.kwargs['schema_id']
        return get_object_or_error(RegistrationSchema, schema_id, self.request)

class RegistrationSchemaFormBlocks(JSONAPIBaseView, generics.ListAPIView):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.SCHEMA_FORM_BLOCKS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = RegistrationSchemaFormBlockSerializer
    view_category = 'schemas'
    view_name = 'registration-schema-form-blocks'
    ordering = ('_order',)

    def get_queryset(self):
        schema_id = self.kwargs.get('schema_id')
        schema = get_object_or_error(RegistrationSchema, schema_id, self.request)
        if schema.schema_version != LATEST_SCHEMA_VERSION or not schema.active:
            raise exceptions.ValidationError('Registration schema must be active.')
        return schema.form_blocks.all()

class RegistrationSchemaFormBlockDetail(JSONAPIBaseView, generics.RetrieveAPIView):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.SCHEMA_FORM_BLOCKS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = RegistrationSchemaFormBlockSerializer
    view_category = 'schemas'
    view_name = 'registration-schema-form-block-detail'

    def get_object(self):
        return get_object_or_error(RegistrationFormBlock, self.kwargs.get('form_block_id'), self.request)
