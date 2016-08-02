from rest_framework import generics
from rest_framework import permissions as drf_permissions

from modularodm import Q

from framework.auth.oauth_scopes import CoreScopes

from website.models import Node

from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.base.filters import ODMFilterMixin
from api.preprints.serializers import PreprintSerializer, PreprintDetailSerializer
from api.nodes.views import NodeMixin, WaterButlerMixin, NodeContributorsList
from api.base.utils import get_object_or_error
from rest_framework.exceptions import NotFound
from api.nodes.serializers import (
    NodeContributorsSerializer
)


class PreprintMixin(NodeMixin):
    serializer_class = PreprintSerializer
    node_lookup_url_kwarg = 'node_id'

    def get_node(self):
        node = get_object_or_error(
            Node,
            self.kwargs[self.node_lookup_url_kwarg],
            display_name='preprint'
        )
        if not node.is_preprint:
            raise NotFound

        return node


class PreprintList(JSONAPIBaseView, generics.ListAPIView, ODMFilterMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NODE_BASE_WRITE]

    serializer_class = PreprintSerializer

    ordering = ('-preprint_created')
    view_category = 'preprints'
    view_name = 'preprint-list'

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        return (
            Q('preprint_file', 'ne', None) &
            Q('is_deleted', 'ne', True) &
            Q('preprint_file', 'ne', None) &
            Q('is_public', 'eq', True)
        )

    # overrides ListAPIView
    def get_queryset(self):
        query = self.get_query_from_request()
        nodes = Node.find(query)

        return [node for node in nodes if node.is_preprint]


class PreprintDetail(JSONAPIBaseView, generics.RetrieveUpdateAPIView, PreprintMixin, WaterButlerMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NODE_BASE_WRITE]

    serializer_class = PreprintDetailSerializer
    view_category = 'preprints'
    view_name = 'preprint-detail'

    def get_object(self):
        return self.get_node()


class PreprintAuthorsList(NodeContributorsList, PreprintMixin):

    view_category = 'preprint'
    view_name = 'preprint-authors'

    def get_serializer_class(self):
        return NodeContributorsSerializer
