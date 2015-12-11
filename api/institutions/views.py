from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import NotFound

from modularodm import Q

from framework.auth.oauth_scopes import CoreScopes

from website.models import Institution, Node, User

from api.base import permissions as base_permissions
from api.base.filters import ODMFilterMixin
from api.base.views import JSONAPIBaseView
from api.base.utils import get_object_or_error
from api.nodes.views import NodeMixin
from api.nodes.serializers import NodeSerializer, NodeDetailSerializer
from api.nodes.permissions import ContributorOrPublic
from api.users.serializers import UserSerializer, UserDetailSerializer

from .serializers import InstitutionSerializer

class InstitutionMixin(object):

    institution_lookup_url_kwarg = 'institution_id'

    def get_institution(self):
        inst = get_object_or_error(
            Institution,
            self.kwargs[self.institution_lookup_url_kwarg],
            display_name='institution'
        )
        return inst


class InstitutionList(JSONAPIBaseView, generics.ListAPIView):
    """
    Verified Institutions affiliated with COS

    Paginated list of institutions

    ##Institution Attributes

    OSF Institutions have the "institutions" `type`.

        name           type               description
        -------------------------------------------------------------------------
        name           string             title of the institution
        id             string             unique identifier in the OSF
        logo_path      string             a path to the institution's static logo

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.INSTITUTION_READ]
    required_write_scopes = [CoreScopes.NULL]
    model_class = Institution

    serializer_class = InstitutionSerializer
    view_category = 'institutions'
    view_name = 'institution-list'

    def get_queryset(self):
        return Institution.find()


class InstitutionDetail(JSONAPIBaseView, generics.RetrieveAPIView, InstitutionMixin):
    """ Details about a given institution.

    ###Permissions

    All institutions are available to be read by everyone. However, no one has write
    permissions for institutions.

    ##Attributes

    OSF Institutions have the "institutions" `type`.

        name           type               description
        -------------------------------------------------------------------------
        name           string             title of the institution
        id             string             unique identifier in the OSF
        logo_path      string             a path to the institution's static logo

    ##Relationships

    ###Nodes
    List of nodes that have this institution as its primary institution.

    ###Users
    List of users that are affiliated with this institution.

    ##Links

        self:  the canonical api endpoint of this node
        html:  this node's page on the OSF website

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.INSTITUTION_READ]
    required_write_scopes = [CoreScopes.NULL]
    model_class = Institution

    serializer_class = InstitutionSerializer
    view_category = 'institutions'
    view_name = 'institution-detail'

    # overrides RetrieveAPIView
    def get_object(self):
        return self.get_institution()


class InstitutionNodeList(JSONAPIBaseView, ODMFilterMixin, generics.ListAPIView, InstitutionMixin):
    """Nodes that have selected an institution as their primary institution.

    ##Permissions
    Only public nodes or ones in which current user is a contributor.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.INSTITUTION_READ, CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NULL]
    model_class = Node

    serializer_class = NodeSerializer
    view_category = 'institutions'
    view_name = 'institution-nodes'

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        inst = self.get_institution()
        inst_query = Q('primary_institution', 'eq', inst)
        base_query = (
            Q('is_deleted', 'ne', True) &
            Q('is_folder', 'ne', True) &
            Q('is_registration', 'eq', False)
        )
        user = self.request.user
        permission_query = Q('is_public', 'eq', True)
        if not user.is_anonymous():
            permission_query = (permission_query | Q('contributors', 'icontains', user._id))

        query = base_query & permission_query & inst_query
        return query

    # overrides RetrieveAPIView
    def get_queryset(self):
        query = self.get_query_from_request()
        return Node.find(query)


class InstitutionNodeDetail(JSONAPIBaseView, generics.RetrieveAPIView, NodeMixin, InstitutionMixin):
    """Detail of a node with this primary institution
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublic
    )

    required_read_scopes = [CoreScopes.INSTITUTION_READ, CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NULL]
    model_class = Node

    serializer_class = NodeDetailSerializer
    view_category = 'institutions'
    view_name = 'institution-node-detail'

    # overrides RetrieveAPIView
    def get_object(self):
        inst = self.get_institution()
        node = self.get_node()
        if node.primary_institution != inst:
            raise NotFound
        return node


class InstitutionUserList(JSONAPIBaseView, ODMFilterMixin, generics.ListAPIView, InstitutionMixin):
    """Users that have been authenticated with the institution.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.INSTITUTION_READ, CoreScopes.USERS_READ]
    required_write_scopes = [CoreScopes.NULL]
    model_class = User

    serializer_class = UserSerializer
    view_category = 'institutions'
    view_name = 'institution-users'

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        inst = self.get_institution()
        query = Q('affiliated_institutions', 'eq', inst)
        return query

    # overrides RetrieveAPIView
    def get_queryset(self):
        query = self.get_query_from_request()
        return User.find(query)


class InstitutionUserDetail(JSONAPIBaseView, generics.RetrieveAPIView, InstitutionMixin):
    """Detail of User that has the institutions as one of its affiliated_institutions.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.INSTITUTION_READ, CoreScopes.USERS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = UserDetailSerializer
    view_category = 'institutions'
    view_name = 'institution-user-detail'

    # overrides RetrieveAPIView
    def get_object(self):
        user = get_object_or_error(
            User,
            self.kwargs['user_id'],
            display_name='user'
        )
        inst = self.get_institution()
        if inst not in user.affiliated_institutions:
            raise NotFound
        return user
