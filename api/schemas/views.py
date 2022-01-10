from rest_framework import generics, permissions as drf_permissions
from framework.auth.oauth_scopes import CoreScopes

from api.base import permissions as base_permissions
from api.base.pagination import MaxSizePagination
from api.base.views import JSONAPIBaseView
from api.base.utils import get_object_or_error
from api.base.filters import ListFilterMixin

from osf.models import (
    RegistrationSchemaBlock,
    RegistrationSchema,
    FileSchema,
    FileSchemaBlock,
)

from api.schemas.serializers import (
    RegistrationSchemaSerializer,
    RegistrationSchemaBlockSerializer,
    FileSchemaSerializer,
    FileSchemaBlockSerializer,
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
        return RegistrationSchema.objects.get_latest_versions(self.request)

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


class FileSchemaList(JSONAPIBaseView, generics.ListAPIView):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.SCHEMA_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = FileSchemaSerializer
    view_category = 'schemas'
    view_name = 'file-schema-list'

    ordering = ('-id',)

    # overrides ListCreateAPIView
    def get_queryset(self):
        return FileSchema.objects.filter(active=True)


class FileSchemaDetail(JSONAPIBaseView, generics.RetrieveAPIView):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.SCHEMA_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = FileSchemaSerializer
    view_category = 'schemas'
    view_name = 'file-schema-detail'

    # overrides RetrieveAPIView
    def get_object(self):
        return get_object_or_error(
            FileSchema,
            self.kwargs['schema_id'],
            self.request,
        )


class RegistrationSchemaBlockList(JSONAPIBaseView, generics.ListAPIView):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    pagination_class = MaxSizePagination

    required_read_scopes = [CoreScopes.SCHEMA_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = RegistrationSchemaBlockSerializer
    view_category = 'schemas'
    view_name = 'registration-schema-block-list'
    ordering = ('_order',)

    def get_queryset(self):
        return get_object_or_error(
            RegistrationSchema,
            self.kwargs['schema_id'],
            self.request,
        ).schema_blocks.all()


class RegistrationSchemaBlockDetail(JSONAPIBaseView, generics.RetrieveAPIView):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.SCHEMA_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = RegistrationSchemaBlockSerializer
    view_category = 'schemas'
    view_name = 'registration-schema-block-detail'

    def get_object(self):
        return get_object_or_error(
            RegistrationSchemaBlock,
            self.kwargs['schema_block_id'],
            self.request,
        )


class FileSchemaBlockList(JSONAPIBaseView, generics.ListAPIView):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    pagination_class = MaxSizePagination

    required_read_scopes = [CoreScopes.SCHEMA_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = FileSchemaBlockSerializer
    view_category = 'schemas'
    view_name = 'file-schema-block-list'
    ordering = ('_order',)

    def get_queryset(self):
        return get_object_or_error(
            FileSchema,
            self.kwargs['schema_id'],
            self.request,
        ).schema_blocks.all()


class FileSchemaBlockDetail(JSONAPIBaseView, generics.RetrieveAPIView):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.SCHEMA_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = FileSchemaBlockSerializer
    view_category = 'schemas'
    view_name = 'file-schema-block-detail'

    def get_object(self):
        return get_object_or_error(
            FileSchemaBlock,
            self.kwargs['schema_block_id'],
            self.request,
        )
