from rest_framework import generics, permissions as drf_permissions

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

    # Overrides NodeMixin for passing in specific node_id, or fetching quickfiles node.
    def get_node(self, check_object_permissions=True, specific_node_id=None):
        node_kwarg = self.kwargs[self.node_lookup_url_kwarg]
        if (specific_node_id and len(specific_node_id) == 5) or len(node_kwarg) == 5:
            node = super(NodeProviderFileMetadataCreate, self).get_node(check_object_permissions, specific_node_id)
        else:
            node = self.get_quickfiles_node(node_kwarg, specific_node_id)

        if not(node.get_addon('osfstorage')):
            raise ValidationError('Node must have OSFStorage Addon.')
        return node

    # Regular nodes or quickfiles nodes both work at this endpoint.
    def get_quickfiles_node(self, node_kwarg, specific_node_id):
        node = get_object_or_error(AbstractNode, specific_node_id if specific_node_id else node_kwarg, self.request, display_name='node')
        self.check_object_permissions(self.request, node)
        return node

    # This endpoint only works for the OsfStorage provider
    def get_provider_id(self):
        provider = self.kwargs.get('provider')
        if provider != 'osfstorage':
            raise ValidationError('This endpoint only valid for the OSFStorage Addon.')
        return provider

    def create(self, request, *args, **kwargs):
        response = super(MoveFile, self).create(request, *args, **kwargs)
        response.status_code = status.HTTP_200_OK if request.data.get('action', '') == 'move' else status.HTTP_201_CREATED
        return response
