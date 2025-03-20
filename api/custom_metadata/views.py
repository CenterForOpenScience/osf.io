from django.contrib.contenttypes.models import ContentType
from django.http import Http404
import rest_framework

from framework.auth.oauth_scopes import CoreScopes

from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView

import osf.models as osfdb
from .permissions import CustomMetadataPermission
from .serializers import CustomFileMetadataSerializer, CustomItemMetadataSerializer


class CustomFileMetadataDetail(JSONAPIBaseView, rest_framework.generics.RetrieveUpdateAPIView):
    permission_classes = (
        CustomMetadataPermission,
        rest_framework.permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.GUIDS_READ]
    required_write_scopes = [CoreScopes.GUID_METADATA_WRITE]

    serializer_class = CustomFileMetadataSerializer
    view_category = 'custom-file-metadata'
    view_name = 'custom-file-metadata-detail'

    def get_object(self):
        try:
            metadata_record = osfdb.GuidMetadataRecord.objects.for_guid(
                self.kwargs['guid_id'],
                allowed_referent_models=(osfdb.BaseFileNode,),
            )
        except osfdb.base.InvalidGuid:
            raise Http404
        self.check_object_permissions(self.request, metadata_record)
        return metadata_record


class CustomItemMetadataDetail(JSONAPIBaseView, rest_framework.generics.RetrieveUpdateAPIView):
    permission_classes = (
        CustomMetadataPermission,
        rest_framework.permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.GUIDS_READ]
    required_write_scopes = [CoreScopes.GUID_METADATA_WRITE]

    serializer_class = CustomItemMetadataSerializer
    view_category = 'custom-item-metadata'
    view_name = 'custom-item-metadata-detail'

    def get_object(self):
        try:
            metadata_record = osfdb.GuidMetadataRecord.objects.for_guid(
                self.kwargs['guid_id'],
                allowed_referent_models=(osfdb.AbstractNode, osfdb.Preprint),
            )
        except osfdb.base.InvalidGuid:
            raise Http404
        # return 'resource_type_general'='Dataset' if Registration provider is  'dataarchive'
        if (
            metadata_record.resource_type_general == ''
            and metadata_record.guid.content_type_id == ContentType.objects.get_for_model(osfdb.Registration).id
        ):
            registration = osfdb.Registration.objects.get(id=metadata_record.guid.object_id)
            if registration and registration.provider and registration.provider._id == 'dataarchive':
                metadata_record.resource_type_general = 'Dataset'
        self.check_object_permissions(self.request, metadata_record)
        return metadata_record
