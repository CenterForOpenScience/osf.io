from modularodm import Q
from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound

from website.models import Node, NodeLog

from api.base.filters import ODMFilterMixin
from api.base.utils import get_user_auth
from api.logs.serializers import NodeLogSerializer
from api.nodes.serializers import NodeSerializer
from api.nodes.utils import get_visible_nodes_for_user

class LogList(generics.ListAPIView, ODMFilterMixin):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
    )
    serializer_class = NodeLogSerializer
    ordering = ('-date', )  # default ordering

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        allowed_node_ids = Node.find(Q('is_public', 'eq', True)).get_keys()
        user = self.request.user
        if not user.is_anonymous():
            allowed_node_ids = [n._id for n in get_visible_nodes_for_user(user)]
        logs_query = Q('__backrefs.logged.node.logs', 'in', list(allowed_node_ids))
        return logs_query

    def get_queryset(self):
        return NodeLog.find(self.get_query_from_request())

class LogNodeList(generics.ListAPIView, ODMFilterMixin):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
    )
    serializer_class = NodeSerializer
    order = ('-date', )

    def get_queryset(self):
        log = NodeLog.load(self.kwargs.get('log_id'))
        if not log:
            raise NotFound(
                detail='No log matching that log_id could be found.'
            )
        else:
            auth_user = get_user_auth(self.request)
            return [
                node for node in log.node__logged
                if node.can_view(auth_user)
            ]
