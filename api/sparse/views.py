from rest_framework.exceptions import MethodNotAllowed
from api.sparse.serializers import SparseNodeSerializer, SparseRegistrationSerializer
from api.nodes.views import (
    NodeDetail,
    NodeChildrenList,
    NodeList,
    LinkedNodesList,
    NodeLinkedRegistrationsList,
)

from api.registrations.views import RegistrationDetail, RegistrationChildrenList, RegistrationList
from api.users.views import UserNodes, UserRegistrations

from api.base.pagination import CursorPagination


class BaseSparseMixin(object):
    view_category = 'sparse'

    pagination_class = CursorPagination
    serializer_class = None

    # overrides NodeList because these endpoints don't allow writing
    @staticmethod
    def perform_create():
        raise MethodNotAllowed

    # overrides NodeDetail because these endpoints don't allow writing
    @staticmethod
    def perform_destroy():
        raise MethodNotAllowed

    # overrides NodeList because these endpoints don't allow writing
    @staticmethod
    def allow_bulk_destroy_resources():
        raise MethodNotAllowed

    def get_serializer_class(self):
        return self.serializer_class


class SparseNodeMixin(BaseSparseMixin):
    serializer_class = SparseNodeSerializer


class SparseRegistrationMixin(BaseSparseMixin):
    serializer_class = SparseRegistrationSerializer


class SparseNodeList(SparseNodeMixin, NodeList):
    pass


class SparseLinkedNodesList(SparseNodeMixin, LinkedNodesList):
    pass


class SparseNodeLinkedRegistrationsList(SparseRegistrationMixin, NodeLinkedRegistrationsList):
    pass


class SparseUserNodeList(SparseNodeMixin, UserNodes):
    pass


class SparseNodeDetail(SparseNodeMixin, NodeDetail):
    pass


class SparseNodeChildrenList(SparseNodeMixin, NodeChildrenList):
    pass


class SparseRegistrationDetail(SparseRegistrationMixin, RegistrationDetail):
    pass


class SparseRegistrationList(SparseRegistrationMixin, RegistrationList):
    pass


class SparseRegistrationChildrenList(SparseRegistrationMixin, RegistrationChildrenList):
    pass


class SparseUserRegistrationList(SparseRegistrationMixin, UserRegistrations):
    pass

