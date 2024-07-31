from rest_framework import generics, permissions as drf_permissions
from django.db.models import Q

from framework.auth.oauth_scopes import CoreScopes

from api.base import permissions as base_permissions
from api.base.parsers import (
    JSONAPIMultipleRelationshipsParser,
    JSONAPIMultipleRelationshipsParserForRegularJSON,
)
from api.base.utils import get_object_or_error
from api.base.views import JSONAPIBaseView
from api.nodes.permissions import ContributorOrPublic
from api.draft_nodes.serializers import DraftNodeSerializer, DraftNodeStorageProviderSerializer
from api.draft_registrations.serializers import DraftRegistrationSerializer
from api.nodes.permissions import IsAdminContributor
from api.nodes.views import (
    NodeStorageProvidersList,
    NodeFilesList,
    NodeStorageProviderDetail,
    NodeFileDetail,
)

from osf.models import DraftNode


class DraftNodeMixin:
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
        ContributorOrPublic,
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


class DraftNodeDraftRegistrationsList(JSONAPIBaseView, generics.ListAPIView, DraftNodeMixin):
    permission_classes = (
        IsAdminContributor,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON)

    required_read_scopes = [CoreScopes.NODE_DRAFT_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NODE_DRAFT_REGISTRATIONS_WRITE]

    serializer_class = DraftRegistrationSerializer
    view_category = 'draft_nodes'
    view_name = 'draft-node-draft-registrations'

    # overrides ListCreateAPIView
    def get_queryset(self):
        node = self.get_node()
        return node.draft_registrations_active


class DraftNodeStorageProvidersList(DraftNodeMixin, NodeStorageProvidersList):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        base_permissions.TokenHasScope,
    )

    view_category = 'draft_nodes'
    serializer_class = DraftNodeStorageProviderSerializer


class DraftNodeStorageProviderDetail(DraftNodeMixin, NodeStorageProviderDetail):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        base_permissions.TokenHasScope,
    )

    view_category = 'draft_nodes'
    serializer_class = DraftNodeStorageProviderSerializer


class DraftNodeFilesList(DraftNodeMixin, NodeFilesList):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.PermissionWithGetter(ContributorOrPublic, 'target'),
        base_permissions.TokenHasScope,
    )
    view_category = 'draft_nodes'


class DraftNodeFileDetail(DraftNodeMixin, NodeFileDetail):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.PermissionWithGetter(ContributorOrPublic, 'target'),
        base_permissions.TokenHasScope,
    )

    view_category = 'draft_nodes'
