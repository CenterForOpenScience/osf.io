from rest_framework import generics
from rest_framework import permissions as drf_permissions
from framework.auth.oauth_scopes import CoreScopes

from api.base.views import JSONAPIBaseView
from api.base import permissions as base_permissions
from api.files.views import FileMixin
from api.file_schema_responses.serializers import FileSchemaResponseSerializer
from api.file_schema_responses.permissions import FileSchemaResponseDetailPermission
from osf.models import FileSchemaResponse


class FileSchemaResponsesList(JSONAPIBaseView, generics.ListAPIView, FileMixin):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = FileSchemaResponseSerializer
    view_category = 'file_schema_responses'
    view_name = 'file-schema-response-list'

    ordering = ('-created',)

    def get_queryset(self):
        return self.get_file().schema_responses.all()


class FileSchemaResponseDetail(JSONAPIBaseView, generics.RetrieveUpdateAPIView, FileMixin):

    permission_classes = (
        FileSchemaResponseDetailPermission,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,

    )

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NODE_FILE_WRITE]

    serializer_class = FileSchemaResponseSerializer
    view_category = 'file_schema_responses'
    view_name = 'file-schema-response-detail'

    def get_object(self):
        return FileSchemaResponse.objects.get(_id=self.kwargs['file_schema_response_id'])
