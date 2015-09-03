from modularodm import Q
from rest_framework import generics, permissions as drf_permissions

from website.models import Node, NodeLog
from api.base.filters import ODMFilterMixin

from api.nodes import serializers as node_serializers

class LogList(generics.ListAPIView, ODMFilterMixin):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
    )
    serializer_class = node_serializers.NodeLogSerializer
    ordering = ('-date', )  # default ordering

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        allowed_node_ids = set(Node.find(Q('is_public', 'eq', True)).get_keys())
        user = self.request.user
        if not user.is_anonymous():
            allowed_node_ids = allowed_node_ids & set(Node.find(Q('contributors', 'icontains', user._id)).get_keys())
        logs_query = Q('__backrefs.logged.node.logs', 'in', list(allowed_node_ids))
        return logs_query

    def get_queryset(self):
        return NodeLog.find(self.get_query_from_request())

class LogNodeList(generics.ListAPIView, ODMFilterMixin):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
    )
    serializer_class = node_serializers.NodeSerializer
    order = ('-date', )

    def get_queryset(self):
        log = NodeLog.load(self.kwargs.get('log_id'))
        if not log:
            return []
        else:
            return log.node__logged
