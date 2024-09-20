import logging

from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import NotFound
from rest_framework.generics import CreateAPIView, RetrieveAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.renderers import JSONRenderer
from rest_framework.views import Response

from api.base import permissions as base_permissions
from api.base.parsers import (
    JSONAPIMultipleRelationshipsParser,
    JSONAPIMultipleRelationshipsParserForRegularJSON,
)
from api.base.versioning import PrivateVersioning
from api.base.views import JSONAPIBaseView
from api.cedar_metadata_records.permissions import CedarMetadataRecordPermission
from api.cedar_metadata_records.serializers import (
    CedarMetadataRecordsCreateSerializer,
    CedarMetadataRecordsDetailSerializer,
)
from framework.auth.oauth_scopes import CoreScopes

from osf.models import CedarMetadataRecord

logger = logging.getLogger(__name__)


class CedarMetadataRecordCreate(JSONAPIBaseView, CreateAPIView):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.CEDAR_METADATA_RECORD_WRITE]

    serializer_class = CedarMetadataRecordsCreateSerializer
    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON)
    model_class = CedarMetadataRecord

    # This view goes under the _/ namespace
    versioning_class = PrivateVersioning
    view_category = 'cedar-metadata-records'
    view_name = 'cedar-metadata-record-list'


class CedarMetadataRecordDetail(JSONAPIBaseView, RetrieveUpdateDestroyAPIView):

    permission_classes = (
        CedarMetadataRecordPermission,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.CEDAR_METADATA_RECORD_READ]
    required_write_scopes = [CoreScopes.CEDAR_METADATA_RECORD_WRITE]

    serializer_class = CedarMetadataRecordsDetailSerializer

    # This view goes under the _/ namespace
    versioning_class = PrivateVersioning
    view_category = 'cedar-metadata-records'
    view_name = 'cedar-metadata-record-detail'

    def get_object(self):
        try:
            record = CedarMetadataRecord.objects.get(_id=self.kwargs['record_id'])
        except CedarMetadataRecord.DoesNotExist:
            raise NotFound
        self.check_object_permissions(self.request, record)
        return record

class CedarMetadataRecordMetadataDownload(JSONAPIBaseView, RetrieveAPIView):

    permission_classes = (
        CedarMetadataRecordPermission,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.CEDAR_METADATA_RECORD_READ]
    required_write_scopes = [CoreScopes.CEDAR_METADATA_RECORD_WRITE]

    renderer_classes = [JSONRenderer]

    # This view goes under the _/ namespace
    versioning_class = PrivateVersioning
    view_category = 'cedar-metadata-records'
    view_name = 'cedar-metadata-record-metadata-download'

    def get_object(self):
        try:
            record = CedarMetadataRecord.objects.get(_id=self.kwargs['record_id'])
        except CedarMetadataRecord.DoesNotExist:
            raise NotFound
        self.check_object_permissions(self.request, record)
        return record

    def get_serializer_class(self):
        return None

    def get(self, request, *args, **kwargs):
        record = self.get_object()
        file_name = f'{record._id}-{record.get_template_name()}-v{record.get_template_version()}.json'
        return Response(record.metadata, headers={'Content-Disposition': f'attachment; filename={file_name}'})
