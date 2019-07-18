from rest_framework.exceptions import MethodNotAllowed
from osf.models.node import Node
from api.nodes.views import NodeList, NodeChildrenList
from api.sparse.serializers import SparseNodeSerializer
from api.users.views import UserNodes

from api.base.pagination import CursorPagination

# Todo: detail view. Return sparse views when available. No joins if at all possible
class SparseNodeMixin(object):
    view_category = 'sparse'
    view_name = 'sparse-node-list'

    pagination_class = CursorPagination

    @staticmethod
    def get_serializer_class():
        return SparseNodeSerializer

    # overrides NodeList because these endpoints don't allow writing
    @staticmethod
    def perform_create():
        raise MethodNotAllowed

    # overrides NodeList because these endpoints don't allow writing
    @staticmethod
    def allow_bulk_destroy_resources():
        raise MethodNotAllowed


class SparseNodeList(SparseNodeMixin, NodeList):
    pass

class SparseUserNodeList(SparseNodeMixin, UserNodes):
    pass


class SparseNodeChildrenList(NodeChildrenList, UserNodes):
    pass
