from django.db.models import F
from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework import exceptions
from rest_framework import status
from rest_framework.response import Response

from framework.auth.oauth_scopes import CoreScopes

from osf.models import OSFUser, Node, Institution, Registration
from osf.utils import permissions as osf_permissions

from api.base import permissions as base_permissions
from api.base.filters import ListFilterMixin
from api.base.views import JSONAPIBaseView
from api.base.serializers import JSONAPISerializer
from api.base.utils import get_object_or_error, get_user_auth
from api.base.pagination import MaxSizePagination
from api.base.parsers import (
    JSONAPIRelationshipParser,
    JSONAPIRelationshipParserForRegularJSON,
)
from api.base.exceptions import RelationshipPostMakesNoChanges
from api.nodes.serializers import NodeSerializer
from api.nodes.filters import NodesFilterMixin
from api.users.serializers import UserSerializer
from api.registrations.serializers import RegistrationSerializer

from api.institutions.authentication import InstitutionAuthentication
from api.institutions.serializers import InstitutionSerializer, InstitutionNodesRelationshipSerializer, InstitutionRegistrationsRelationshipSerializer
from api.institutions.permissions import UserIsAffiliated

class InstitutionMixin(object):
    """Mixin with convenience method get_institution
    """

    institution_lookup_url_kwarg = 'institution_id'

    def get_institution(self):
        inst = get_object_or_error(
            Institution,
            self.kwargs[self.institution_lookup_url_kwarg],
            self.request,
            display_name='institution'
        )
        return inst


class InstitutionList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/institutions_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.INSTITUTION_READ]
    required_write_scopes = [CoreScopes.NULL]
    model_class = Institution

    pagination_class = MaxSizePagination
    serializer_class = InstitutionSerializer
    view_category = 'institutions'
    view_name = 'institution-list'

    ordering = ('name', )

    def get_default_queryset(self):
        return Institution.objects.filter(_id__isnull=False, is_deleted=False)

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()


class InstitutionDetail(JSONAPIBaseView, generics.RetrieveAPIView, InstitutionMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/institutions_detail).
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


class InstitutionNodeList(JSONAPIBaseView, generics.ListAPIView, InstitutionMixin, NodesFilterMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/institutions_node_list).
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

    ordering = ('-modified', )

    # overrides NodesFilterMixin
    def get_default_queryset(self):
        institution = self.get_institution()
        return (
            institution.nodes.filter(is_public=True, is_deleted=False, type='osf.node')
            .select_related('node_license', 'preprint_file')
            .include('contributor__user__guids', 'root__guids', 'tags', limit_includes=10)
            .annotate(region=F('addons_osfstorage_node_settings__region___id'))
        )

    # overrides RetrieveAPIView
    def get_queryset(self):
        if self.request.version < '2.2':
            return self.get_queryset_from_request().get_roots()
        return self.get_queryset_from_request()


class InstitutionUserList(JSONAPIBaseView, ListFilterMixin, generics.ListAPIView, InstitutionMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/institutions_users_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.INSTITUTION_READ, CoreScopes.USERS_READ]
    required_write_scopes = [CoreScopes.NULL]
    model_class = OSFUser

    serializer_class = UserSerializer
    view_category = 'institutions'
    view_name = 'institution-users'

    ordering = ('-id',)

    def get_default_queryset(self):
        institution = self.get_institution()
        return institution.osfuser_set.all()

    # overrides RetrieveAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()


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
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/institutions_registration_list).
    """
    serializer_class = RegistrationSerializer
    view_name = 'institution-registrations'

    ordering = ('-modified', )

    def get_default_queryset(self):
        institution = self.get_institution()
        return institution.nodes.filter(is_deleted=False, is_public=True, type='osf.registration', retraction__isnull=True)

    def get_queryset(self):
        return self.get_queryset_from_request()

class InstitutionRegistrationsRelationship(JSONAPIBaseView, generics.RetrieveDestroyAPIView, generics.CreateAPIView, InstitutionMixin):
    """ Relationship Endpoint for Institution -> Registrations Relationship

    Used to set, remove, update and retrieve the affiliated_institution of registrations with this institution

    ##Actions

    ###Create

        Method:        POST
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "registrations",   # required
                           "id": <registration_id>   # required
                         }]
                       }
        Success:       201

    This requires write permissions on the registrations requested and for the user making the request to
    have the institution affiliated in their account.

    ###Destroy

        Method:        DELETE
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "registrations",   # required
                           "id": <registration_id>   # required
                         }]
                       }
        Success:       204

    This requires write permissions in the registrations requested.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        UserIsAffiliated
    )
    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ, CoreScopes.INSTITUTION_READ]
    required_write_scopes = [CoreScopes.NODE_REGISTRATIONS_WRITE]
    serializer_class = InstitutionRegistrationsRelationshipSerializer
    parser_classes = (JSONAPIRelationshipParser, JSONAPIRelationshipParserForRegularJSON, )

    view_category = 'institutions'
    view_name = 'institution-relationships-registrations'

    def get_object(self):
        inst = self.get_institution()
        auth = get_user_auth(self.request)
        registrations = inst.nodes.filter(is_deleted=False, type='osf.registration').can_view(user=auth.user, private_link=auth.private_link)
        ret = {
            'data': registrations,
            'self': inst
        }
        self.check_object_permissions(self.request, ret)
        return ret

    def perform_destroy(self, instance):
        data = self.request.data['data']
        user = self.request.user
        ids = [datum['id'] for datum in data]
        registrations = []
        for id_ in ids:
            registration = Registration.load(id_)
            if not registration.has_permission(user, osf_permissions.WRITE):
                raise exceptions.PermissionDenied(detail='Write permission on registration {} required'.format(id_))
            registrations.append(registration)

        for registration in registrations:
            registration.remove_affiliated_institution(inst=instance['self'], user=user)
            registration.save()

    def create(self, *args, **kwargs):
        try:
            ret = super(InstitutionRegistrationsRelationship, self).create(*args, **kwargs)
        except RelationshipPostMakesNoChanges:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return ret

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

    This requires write permissions on the nodes requested and for the user making the request to
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

    This requires write permissions in the nodes requested.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        UserIsAffiliated
    )
    required_read_scopes = [CoreScopes.NODE_BASE_READ, CoreScopes.INSTITUTION_READ]
    required_write_scopes = [CoreScopes.NODE_BASE_WRITE]
    serializer_class = InstitutionNodesRelationshipSerializer
    parser_classes = (JSONAPIRelationshipParser, JSONAPIRelationshipParserForRegularJSON, )

    view_category = 'institutions'
    view_name = 'institution-relationships-nodes'

    def get_object(self):
        inst = self.get_institution()
        auth = get_user_auth(self.request)
        nodes = inst.nodes.filter(is_deleted=False, type='osf.node').can_view(user=auth.user, private_link=auth.private_link)
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
            if not node.has_permission(user, osf_permissions.WRITE):
                raise exceptions.PermissionDenied(detail='Write permission on node {} required'.format(id_))
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
