import io

from django.http import FileResponse

from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import ValidationError
from framework.auth.oauth_scopes import CoreScopes

from api.base.permissions import PermissionWithGetter
from api.base import utils
from api.base.views import JSONAPIBaseView
from api.base import permissions as base_permissions
from api.nodes.permissions import ContributorOrPublic
from api.files.views import FileMixin
from api.file_schema_responses.serializers import FileSchemaResponseSerializer


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
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NODE_FILE_WRITE]

    serializer_class = FileSchemaResponseSerializer
    view_category = 'file_schema_responses'
    view_name = 'file-schema-response-detail'

    def get_object(self):
        return utils.get_object_or_error(
            self.get_file().schema_responses.filter(_id=self.kwargs['file_schema_response_id']),
            request=self.request,
        )


class FileSchemaResponseDownload(JSONAPIBaseView, generics.RetrieveAPIView, FileMixin):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        PermissionWithGetter(ContributorOrPublic, 'parent'),
    )

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'file_schema_responses'
    view_name = 'file-schema-response-download'

    def get_object(self):
        return utils.get_object_or_error(
            self.get_file().schema_responses.filter(
                _id=self.kwargs['file_schema_response_id'],
            ).select_related(
                'schema',
                'file',
            ),
            request=self.request,
        )

    def get(self, request, **kwargs):
        file_type = self.request.query_params.get('export', 'json')
        record = self.get_object()
        try:
            content = io.BytesIO(record.serialize(format=file_type).encode())
            response = FileResponse(content)
        except ValueError as e:
            detail = str(e).replace('.', '')
            raise ValidationError(detail='{} for metadata file export.'.format(detail))
        file_name = 'file_metadata_{}_{}.{}'.format(record.schema._id, record.file.name, file_type)
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(file_name)
        response['Content-Type'] = 'application/{}'.format(file_type)
        return response
