from rest_framework import generics
from modularodm import Q

from website.models import Institution, Node, User

from api.institutions.serializers import InstitutionSerializer, InstitutionDetailSerializer

from api.nodes.serializers import NodeSerializer, NodeDetailSerializer
from api.users.serializers import UserSerializer, UserDetailSerializer

from api.base.filters import ODMFilterMixin
from api.base.views import JSONAPIBaseView

class InstitutionList(JSONAPIBaseView, ODMFilterMixin, generics.ListAPIView):
    permission_classes = ()

    required_read_scopes = []
    required_write_scopes = []
    model_class = Institution

    serializer_class = InstitutionSerializer
    view_category = 'institutions'
    view_name = 'institution-list'

    def get_default_odm_query(self):
        query = None
        return query

    def get_queryset(self):
        query = self.get_query_from_request()
        return Institution.find(query)


class InstitutionDetail(JSONAPIBaseView):
    permission_classes = ()

    required_read_scopes = []
    required_write_scopes = []
    model_class = Institution

    serializer_class = InstitutionDetailSerializer
    view_category = 'institutions'
    view_name = 'institution-detail'

class InstitutionNodeList(JSONAPIBaseView, ODMFilterMixin, generics.ListAPIView):
    permission_classes = ()

    required_read_scopes = []
    required_write_scopes = []
    model_class = Node

    serializer_class = NodeSerializer
    view_category = 'institutions'
    view_name = 'institution-nodes'

    def get_default_odm_query(self):
        query = Q('primary_institution', 'ne', None)
        return query

    def get_queryset(self):
        query = self.get_query_from_request()
        return Node.find(query)

class InstitutionNodeDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    permission_classes = ()

    required_read_scopes = []
    required_write_scopes = []
    model_class = Node

    serializer_class = NodeDetailSerializer
    view_category = 'institutions'
    view_name = 'institution-node-serializer'

    def get_object(self):
        pass

class InstitutionUserList(JSONAPIBaseView, ODMFilterMixin, generics.ListAPIView):
    permission_classes = ()

    required_read_scopes = []
    required_write_scopes = []
    model_class = User

    serializer_class = UserSerializer
    view_category = 'institutions'
    view_name = 'institution-users'

    def get_default_odm_query(self):
        query = Q('affiliated_institutions', 'ne', None)
        return query

    def get_queryset(self):
        query = self.get_query_from_request()
        return User.find(query)

class InstitutionUserDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    permission_classes = ()

    required_read_scopes = []
    required_write_scopes = []

    serializer_class = UserDetailSerializer
    view_category = 'institutions'
    view_name = 'institution-user-detail'

    def get_object(self):
        pass
