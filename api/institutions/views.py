from rest_framework import generics
from rest_framework import permissions as drf_permissions

from modularodm import Q

from framework.auth.oauth_scopes import CoreScopes

from website.models import Institution, Node, User

from api.base import permissions as base_permissions
from api.base.filters import ODMFilterMixin
from api.base.views import JSONAPIBaseView
from api.base.utils import get_object_or_error
from api.nodes.serializers import NodeSerializer
from api.users.serializers import UserSerializer

from .serializers import InstitutionSerializer

class InstitutionMixin(object):
    """Mixin with convenience method get_institution
    """

    institution_lookup_url_kwarg = 'institution_id'

    def get_institution(self):
        inst = get_object_or_error(
            Institution,
            self.kwargs[self.institution_lookup_url_kwarg],
            display_name='institution'
        )
        return inst


class InstitutionList(JSONAPIBaseView, generics.ListAPIView, ODMFilterMixin):
    """
    Paginated list of verified Institutions affiliated with COS

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

    def get_default_odm_query(self):
        return Q('_id', 'ne', None)

    # overrides ListAPIView
    def get_queryset(self):
        return Institution.find(self.get_query_from_request())


class InstitutionDetail(JSONAPIBaseView, generics.RetrieveAPIView, InstitutionMixin):
    """ Details about a given institution.

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

        self:  the canonical api endpoint of this institution
        html:  this institution's page on the OSF website

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
