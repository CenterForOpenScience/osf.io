from __future__ import unicode_literals

from rest_framework import generics
from rest_framework import permissions

from api.base.views import JSONAPIBaseView
from api.base import permissions as base_permissions
from api.base.utils import get_object_or_error
from api.requests.permissions import NodeRequestPermission
from api.requests.serializers import NodeRequestSerializer
from framework.auth.oauth_scopes import CoreScopes
from osf.models import Node, NodeRequest


class NodeRequestMixin(object):
    serializer_class = NodeRequestSerializer
    node_lookup_url_kwarg = 'node_id'
    node_request_lookup_url_kwarg = 'request_id'

    def get_noderequest(self, check_object_permissions=True):
        node_request = get_object_or_error(
            NodeRequest,
            self.kwargs[self.node_request_lookup_url_kwarg],
            self.request,
            display_name='node request'
        )

        # May raise a permission denied
        if check_object_permissions:
            self.check_object_permissions(self.request, node_request)

        return node_request

    def get_node(self, check_object_permissions=True):
        node = get_object_or_error(
            Node,
            self.kwargs[self.node_lookup_url_kwarg],
            self.request,
            display_name='node'
        )

        # May raise a permission denied
        if check_object_permissions:
            self.check_object_permissions(self.request, node)

        return node


class NodeRequestDetail(JSONAPIBaseView, generics.RetrieveAPIView, NodeRequestMixin):
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        NodeRequestPermission
    )

    required_read_scopes = [CoreScopes.NODE_REQUESTS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = NodeRequestSerializer

    view_category = 'requests'
    view_name = 'node-request-detail'

    def get_object(self):
        return self.get_noderequest()
