from __future__ import unicode_literals
import logging

from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView

from api.base import permissions as base_permissions
from api.base.filters import ListFilterMixin
from api.base.parsers import (
    JSONAPIMultipleRelationshipsParser,
    JSONAPIMultipleRelationshipsParserForRegularJSON,
)
from api.base.versioning import PrivateVersioning
from api.base.views import JSONAPIBaseView
from api.cedar_metadata_records.permissions import CedarMetadataRecordPermission
from api.cedar_metadata_records.serializers import CedarMetadataRecordsSerializer, CedarMetadataRecordsCreateSerializer

from framework.auth.oauth_scopes import CoreScopes

from osf.models import CedarMetadataRecord

logger = logging.getLogger(__name__)


class CedarMetadataRecordList(JSONAPIBaseView, ListCreateAPIView, ListFilterMixin):

    permission_classes = (
        CedarMetadataRecordPermission,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NODE_BASE_WRITE, CoreScopes.NODE_FILE_WRITE, CoreScopes.NODE_REGISTRATIONS_WRITE]

    serializer_class = CedarMetadataRecordsCreateSerializer
    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON, )
    model_class = CedarMetadataRecord

    # This view goes under the _/ namespace
    versioning_class = PrivateVersioning
    view_category = 'cedar-metadata-records'
    view_name = 'cedar-metadata-record-list'

    def get_default_queryset(self):
        return CedarMetadataRecord.objects.filter(is_published=True)

    def get_queryset(self):
        return self.get_queryset_from_request()


class CedarMetadataRecordDetail(JSONAPIBaseView, RetrieveUpdateDestroyAPIView):

    permission_classes = (
        CedarMetadataRecordPermission,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.NODE_BASE_READ, CoreScopes.NODE_FILE_READ, CoreScopes.NODE_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NODE_BASE_WRITE, CoreScopes.NODE_FILE_WRITE, CoreScopes.NODE_REGISTRATIONS_WRITE]

    serializer_class = CedarMetadataRecordsSerializer

    # This view goes under the _/ namespace
    versioning_class = PrivateVersioning
    view_category = 'cedar-metadata-records'
    view_name = 'cedar-metadata-record-detail'

    def get_object(self):
        try:
            return CedarMetadataRecord.objects.get(_id=self.kwargs['record_id'])
        except CedarMetadataRecord.DoesNotExist:
            raise NotFound
