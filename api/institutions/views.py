from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework import exceptions
from rest_framework import status
from rest_framework.response import Response

from modularodm import Q

from framework.auth.oauth_scopes import CoreScopes

from website.models import Node, User, Institution
from website.util import permissions as osf_permissions

from api.base import permissions as base_permissions
from api.base.filters import ODMFilterMixin
from api.base.views import JSONAPIBaseView
from api.base.serializers import JSONAPISerializer
from api.base.utils import get_object_or_error, get_user_auth
from api.base.parsers import (
    JSONAPIRelationshipParser,
    JSONAPIRelationshipParserForRegularJSON,
)
from api.base.exceptions import RelationshipPostMakesNoChanges
from api.nodes.serializers import NodeSerializer
from api.users.serializers import UserSerializer

from .authentication import InstitutionAuthentication
from .serializers import InstitutionSerializer, InstitutionNodesRelationshipSerializer
from .permissions import UserIsAffiliated

class InstitutionMixin(object):
    """Mixin with convenience method get_institution
    """

    institution_lookup_url_kwarg = 'institution_id'

    def get_institution(self):
        inst = get_object_or_error(
            Institution,
            self.kwargs[self.institution_lookup_url_kwarg],
            display_name='institution',
            allow_institution=True
        )
        return inst


class InstitutionList(JSONAPIBaseView, generics.ListAPIView, ODMFilterMixin):
    """
    Paginated list of verified Institutions affiliated with COS

    ##Institution Attributes

    OSF Institutions have the "institutions" `type`.

        name           type               description
        =========================================================================
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

    ordering = ('name', )

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
        =========================================================================
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

    ordering = ('-date_modified', )

    base_node_query = (
        Q('is_deleted', 'ne', True) &
        Q('is_folder', 'ne', True) &
        Q('is_registration', 'eq', False) &
        Q('parent_node', 'eq', None)
    )

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        base_query = self.base_node_query
        user = self.request.user
        permission_query = Q('is_public', 'eq', True)
        if not user.is_anonymous():
            permission_query = (permission_query | Q('contributors', 'eq', user._id))

        query = base_query & permission_query
        return query

    # overrides RetrieveAPIView
    def get_queryset(self):
        inst = self.get_institution()
        query = self.get_query_from_request()
        return Node.find_by_institutions(inst, query)


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
        query = Q('_affiliated_institutions', 'eq', inst.node)
        return query

    # overrides RetrieveAPIView
    def get_queryset(self):
        query = self.get_query_from_request()
        return User.find(query)


class InstitutionAuth(JSONAPIBaseView, generics.CreateAPIView):
    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
    )

    serializer_class = JSONAPISerializer

    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.NULL]
    authentication_classes = (InstitutionAuthentication, )
    view_category = 'institutions'
    view_name = 'institution-auth'

    def post(self, request, *args, **kwargs):
        return Response(status=status.HTTP_204_NO_CONTENT)


class InstitutionRegistrationList(InstitutionNodeList):
    """Registrations have selected an institution as their primary institution.
    """

    view_name = 'institution-registrations'

    base_node_query = (
        Q('is_deleted', 'ne', True) &
        Q('is_folder', 'ne', True) &
        Q('is_registration', 'eq', True)
    )

    ordering = ('-date_modified', )

    def get_queryset(self):
        inst = self.get_institution()
        query = self.get_query_from_request()
        nodes = Node.find_by_institutions(inst, query)
        return [node for node in nodes if not node.is_retracted]

class InstitutionNodesRelationship(JSONAPIBaseView, generics.RetrieveDestroyAPIView, generics.CreateAPIView, InstitutionMixin):
    """ Relationship Endpoint for Institution -> Nodes Relationship

    Used to set, remove, update and retrieve the affiliated_institution of nodes with this institution

    ##Actions

    ###Create

        Method:        POST
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "nodes",   # required
                           "id": <node_id>   # required
                         }]
                       }
        Success:       201

    This requires admin permissions on the nodes requested and for the user making the request to
    have the institution affiliated in their account.

    ###Destroy

        Method:        DELETE
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "nodes",   # required
                           "id": <node_id>   # required
                         }]
                       }
        Success:       204

    This requires admin permissions in the nodes requested.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        UserIsAffiliated
    )
    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.NULL]
    serializer_class = InstitutionNodesRelationshipSerializer
    parser_classes = (JSONAPIRelationshipParser, JSONAPIRelationshipParserForRegularJSON, )

    view_category = 'institutions'
    view_name = 'institution-relationships-nodes'

    def get_object(self):
        inst = self.get_institution()
        auth = get_user_auth(self.request)
        nodes = [node for node in Node.find_by_institutions(inst, Q('is_registration', 'eq', False) & Q('is_deleted', 'ne', True)) if node.is_public or node.can_view(auth)]
        ret = {
            'data': nodes,
            'self': inst
        }
        self.check_object_permissions(self.request, ret)
        return ret

    def perform_destroy(self, instance):
        data = self.request.data['data']
        user = self.request.user
        ids = [datum['id'] for datum in data]
        nodes = []
        for id_ in ids:
            node = Node.load(id_)
            if not node.has_permission(user, osf_permissions.ADMIN):
                raise exceptions.PermissionDenied
            nodes.append(node)

        for node in nodes:
            node.remove_affiliated_institution(inst=instance['self'], user=user)
            node.save()

    def create(self, *args, **kwargs):
        try:
            ret = super(InstitutionNodesRelationship, self).create(*args, **kwargs)
        except RelationshipPostMakesNoChanges:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return ret
