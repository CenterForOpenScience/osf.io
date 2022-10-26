from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework import permissions as drf_permissions

from framework.auth.oauth_scopes import CoreScopes

from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView

from osf.metadata.gather import gather_guid_graph
from .parsers import JSONAPILDParser
# from .serializers import MetadataRecordSerializer


class MetadataRecordDetail(JSONAPIBaseView):
    permission_classes = (
        # TODO: check permissions on guid referent
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.GUIDS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = MetadataRecordSerializer
    view_category = 'metadata-records'
    view_name = 'metadata-record-detail'

    def get(self, request):
        raise NotImplementedError

    def patch(self, request):
        pass

class GuidMetadataDownload(JSONAPIBaseView):

    view_category = 'metadata-records'
    view_name = 'metadata-record-download'

    def get(self, request, guid_id, serializer_name, **kwargs):
        graph = gather_guid_graph(guid_id, sparse=False)
        return HttpResponse(
            graph.serialize(format=serializer_name, auto_compact=True),
            headers={
                'Content-Type': 'text/plain',
            },
        )

class DirectMetadataRecordDetail(APIView):
    parser_classes = (JSONAPILDParser,)

    def get(self, request):
        raise NotImplementedError

    def patch(self, request):
        raise NotImplementedError
