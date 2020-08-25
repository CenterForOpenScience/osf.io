from rest_framework import generics, permissions as drf_permissions
from django.db.models import Q

from framework.auth.oauth_scopes import CoreScopes

from api.base import permissions as base_permissions
from api.base.utils import get_object_or_error
from api.base.views import JSONAPIBaseView
from api.draft_nodes.permissions import ContributorOnDraftRegistration
from api.draft_nodes.serializers import DraftNodeSerializer, DraftNodeStorageProviderSerializer

from api.nodes.views import (
    NodeStorageProvidersList,
    NodeFilesList,
    NodeStorageProviderDetail,
    NodeFileDetail,
)

from osf.models import DraftNode


class DraftNodeMixin(object):
    """Mixin with convenience methods for retrieving the current draft node based on the
    current URL. By default, fetches the current node based on the node_id kwarg.
    """

    node_lookup_url_kwarg = 'node_id'

    def get_node(self, check_object_permissions=True):
        node = get_object_or_error(
            DraftNode,
            Q(guids___id=self.kwargs['node_id']),
            request=self.request,
            display_name='node',
        )

        if check_object_permissions:
            self.check_object_permissions(self.request, node)
        return node


class DraftNodeDetail(JSONAPIBaseView, generics.RetrieveAPIView, DraftNodeMixin):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOnDraftRegistration,
        base_permissions.TokenHasScope,
    )

    serializer_class = DraftNodeSerializer
    view_category = 'draft_nodes'
    view_name = 'draft-node-detail'

    required_read_scopes = [CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NULL]

    # overrides RetrieveAPIView
    def get_object(self):
        return self.get_node()


class DraftNodeStorageProvidersList(DraftNodeMixin, NodeStorageProvidersList):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOnDraftRegistration,
        base_permissions.TokenHasScope,
    )

    view_category = 'draft_nodes'
    serializer_class = DraftNodeStorageProviderSerializer


class DraftNodeStorageProviderDetail(DraftNodeMixin, NodeStorageProviderDetail):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOnDraftRegistration,
        base_permissions.TokenHasScope,
    )

    view_category = 'draft_nodes'
    serializer_class = DraftNodeStorageProviderSerializer


class DraftNodeFilesList(DraftNodeMixin, NodeFilesList):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.PermissionWithGetter(ContributorOnDraftRegistration, 'target'),
        base_permissions.TokenHasScope,
    )
    view_category = 'draft_nodes'


class DraftNodeFileDetail(DraftNodeMixin, NodeFileDetail):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.PermissionWithGetter(ContributorOnDraftRegistration, 'target'),
        base_permissions.TokenHasScope,
    )

    view_category = 'draft_nodes'
