from rest_framework.exceptions import MethodNotAllowed
from api.sparse.serializers import SparseNodeSerializer, SparseRegistrationSerializer
from api.nodes.views import NodeList, NodeChildrenList
from api.registrations.views import RegistrationList, RegistrationChildrenList
from api.users.views import UserNodes, UserRegistrations

from api.base.pagination import CursorPagination


class BaseSparseMixin(object):
    view_category = 'sparse'

    pagination_class = CursorPagination

    # overrides NodeList because these endpoints don't allow writing
    @staticmethod
    def perform_create():
        raise MethodNotAllowed

    # overrides NodeList because these endpoints don't allow writing
    @staticmethod
    def allow_bulk_destroy_resources():
        raise MethodNotAllowed


class SparseNodeMixin(BaseSparseMixin):
    view_name = 'sparse-node-list'

    def get_serializer_class(self):
        return SparseNodeSerializer


class SparseRegistrationMixin(BaseSparseMixin):
    view_name = 'sparse-registration-list'

    def get_serializer_class(self):
        return SparseRegistrationSerializer


class SparseNodeList(SparseNodeMixin, NodeList):
    pass


class SparseUserNodeList(SparseNodeMixin, UserNodes):
    pass


class SparseNodeChildrenList(SparseNodeMixin, NodeChildrenList):
    pass


class SparseRegistrationList(SparseRegistrationMixin, RegistrationList):
    pass


class SparseRegistrationChildrenList(SparseRegistrationMixin, RegistrationChildrenList):
    pass


class SparseUserRegistrationList(SparseRegistrationMixin, UserRegistrations):
    pass

