from django.http import HttpResponse
import rest_framework

from framework.auth.oauth_scopes import CoreScopes

from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView

import osf.models as osfdb
from osf.metadata.gather import gather_deep_metadata
from .parsers import JSONAPILDParser
from .serializers import MetadataRecordJSONAPISerializer


class MetadataRecordDetail(rest_framework.generics.RetrieveUpdateAPIView):
    permission_classes = (
        # TODO: check permissions on guid referent
        rest_framework.permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.GUIDS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = MetadataRecordJSONAPISerializer
    view_category = 'metadata-records'
    view_name = 'metadata-record-detail'

    queryset = osfdb.Guid.objects.all()
    lookup_url_kwarg = 'guid_id'
    lookup_field = '_id'

    # def get_serializer_class(self, request, guid_id):


class GuidMetadataDownload(JSONAPIBaseView):

    view_category = 'metadata-records'
    view_name = 'metadata-record-download'

    def get(self, request, guid_id, serializer_name, **kwargs):
        graph = gather_deep_metadata(guid_id, max_guids=666)
        return HttpResponse(
            graph.serialize(format=serializer_name, auto_compact=True),
            headers={
                'Content-Type': 'text/plain',
            },
        )

class DirectMetadataRecordDetail(rest_framework.views.APIView):
    parser_classes = (JSONAPILDParser,)

    def get(self, request):
        raise NotImplementedError

    def patch(self, request):
        raise NotImplementedError


# class FileMetadataRecordDetail(JSONAPIBaseView, generics.RetrieveUpdateAPIView, FileMixin):
#
#     record_lookup_url_kwarg = 'record_id'
#     permission_classes = (
#         drf_permissions.IsAuthenticatedOrReadOnly,
#         base_permissions.TokenHasScope,
#         FileMetadataRecordPermission(ContributorOrPublic),
#         FileMetadataRecordPermission(ReadOnlyIfRegistration),
#     )
#
#     required_read_scopes = [CoreScopes.NODE_FILE_READ]
#     required_write_scopes = [CoreScopes.NODE_FILE_WRITE]
#
#     serializer_class = FileMetadataRecordSerializer
#     view_category = 'files'
#     view_name = 'metadata-record-detail'
#
#     def get_object(self):
#         return utils.get_object_or_error(
#             self.get_file().records.filter(_id=self.kwargs[self.record_lookup_url_kwarg]),
#             request=self.request,
#         )
#
#
# class FileMetadataRecordDownload(JSONAPIBaseView, generics.RetrieveAPIView, FileMixin):
#
#     record_lookup_url_kwarg = 'record_id'
#     permission_classes = (
#         drf_permissions.IsAuthenticatedOrReadOnly,
#         base_permissions.TokenHasScope,
#         PermissionWithGetter(ContributorOrPublic, 'target'),
#     )
#
#     required_read_scopes = [CoreScopes.NODE_FILE_READ]
#     required_write_scopes = [CoreScopes.NULL]
#
#     view_category = 'files'
#     view_name = 'metadata-record-download'
#
#     def get_serializer_class(self):
#         return None
#
#     def get_object(self):
#         return utils.get_object_or_error(
#             self.get_file().records.filter(_id=self.kwargs[self.record_lookup_url_kwarg]).select_related('schema', 'file'),
#             request=self.request,
#         )
#
#     def get(self, request, **kwargs):
#         file_type = self.request.query_params.get('export', 'json')
#         record = self.get_object()
#         try:
#             content = io.BytesIO(record.serialize(format=file_type).encode())
#             response = FileResponse(content)
#         except ValueError as e:
#             detail = str(e).replace('.', '')
#             raise ValidationError(detail='{} for metadata file export.'.format(detail))
#         file_name = 'file_metadata_{}_{}.{}'.format(record.schema._id, record.file.name, file_type)
#         response['Content-Disposition'] = 'attachment; filename="{}"'.format(file_name)
#         response['Content-Type'] = 'application/{}'.format(file_type)
#         return response
