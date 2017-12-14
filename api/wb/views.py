from rest_framework import generics, status, permissions as drf_permissions

from osf.models import AbstractNode
from api.base import permissions as base_permissions
from api.base.utils import get_object_or_error
from api.base.views import JSONAPIBaseView
from api.base.views import (
    WaterButlerMixin
)
from api.nodes.views import NodeMixin
from api.nodes.permissions import (
    ContributorOrPublic,
    ExcludeWithdrawals,
)
from api.wb.serializers import (
    NodeProviderFileMetadataCreateSerializer

)
from api.base.parsers import HMACSignedParser
from framework.auth.oauth_scopes import CoreScopes


class MoveFile(JSONAPIBaseView, generics.CreateAPIView, NodeMixin, WaterButlerMixin):
    """
    View for creating metadata for file move/copy in osfstorage.  Only WaterButler should talk to this endpoint.
    To move/copy a file, send a request to WB, and WB will call this view.
    """
    parser_classes = (HMACSignedParser,)

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        ExcludeWithdrawals,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NODE_FILE_WRITE]

    serializer_class = NodeProviderFileMetadataCreateSerializer
    view_category = 'nodes'
    view_name = 'node-provider-file-metadata'

    # overrides CreateApiView
    def perform_create(self, serializer):
        source = AbstractNode.load(self.kwargs.get('node_id'))
        return serializer.save(action='move', source_node=source)

    def create(self, request, *args, **kwargs):
        response = super(MoveFile, self).create(request, *args, **kwargs)
        response.status_code = status.HTTP_200_OK if request.data.get('action', '') == 'move' else status.HTTP_201_CREATED
        return response
