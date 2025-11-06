from django.conf import settings
from django.db.models import F
from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework import exceptions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.settings import api_settings

from framework.auth.oauth_scopes import CoreScopes

from osf.models import OSFUser, Node, Institution, Registration
from osf.metrics.reports import InstitutionalUserReport, InstitutionMonthlySummaryReport
from osf.metrics.utils import YearMonth
from osf.utils import permissions as osf_permissions

from api.base import permissions as base_permissions
from api.base.elasticsearch_dsl_views import ElasticsearchListView
from api.base.filters import ListFilterMixin
from api.base.views import JSONAPIBaseView
from api.base.serializers import JSONAPISerializer
from api.base.utils import get_object_or_error, get_user_auth
from api.base.pagination import MaxSizePagination, JSONAPINoPagination
from api.base.parsers import (
    JSONAPIRelationshipParser,
    JSONAPIRelationshipParserForRegularJSON,
)
from api.base.exceptions import RelationshipPostMakesNoChanges
from api.metrics.permissions import IsInstitutionalMetricsUser
from api.metrics.renderers import (
    MetricsReportsCsvRenderer,
    MetricsReportsTsvRenderer,
    MetricsReportsJsonRenderer,
)
from api.nodes.serializers import NodeSerializer
from api.nodes.filters import NodesFilterMixin
from api.users.serializers import UserSerializer
from api.registrations.serializers import RegistrationSerializer

from api.institutions.authentication import InstitutionAuthentication
from api.institutions.serializers import (
    InstitutionSerializer,
    InstitutionNodesRelationshipSerializer,
    InstitutionRegistrationsRelationshipSerializer,
    InstitutionDepartmentMetricsSerializer,
    InstitutionUserMetricsSerializer,
    InstitutionSummaryMetricsSerializer,
)
from api.institutions.permissions import UserIsAffiliated


class InstitutionMixin:
    """Mixin with convenience method get_institution
    """

    institution_lookup_url_kwarg = 'institution_id'

    def get_institution(self):
        inst = get_object_or_error(
            Institution,
            self.kwargs[self.institution_lookup_url_kwarg],
            self.request,
            display_name='institution',
        )
        return inst


class InstitutionList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin):
    """See [documentation for this endpoint](https://developer.osf.io/#operation/institutions_list).
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

    ordering = ('name',)

    def get_default_queryset(self):
        return Institution.objects.filter(_id__isnull=False, is_deleted=False)

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()


class InstitutionDetail(JSONAPIBaseView, generics.RetrieveAPIView, InstitutionMixin):
    """See [documentation for this endpoint](https://developer.osf.io/#operation/institutions_detail).
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
    """See [documentation for this endpoint](https://developer.osf.io/#operation/institutions_node_list).
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

    ordering = ('-modified',)

    # overrides NodesFilterMixin
    def get_default_queryset(self):
        institution = self.get_institution()
        return (
            institution.nodes.filter(is_public=True, is_deleted=False, type='osf.node')
            .select_related('node_license')
            .prefetch_related('contributor_set__user__guids', 'root__guids', 'tags')
            .annotate(region=F('addons_osfstorage_node_settings__region___id'))
        )

    # overrides RetrieveAPIView
    def get_queryset(self):
        if self.request.version < '2.2':
            return self.get_queryset_from_request().get_roots()
        return self.get_queryset_from_request()


class InstitutionUserList(JSONAPIBaseView, ListFilterMixin, generics.ListAPIView, InstitutionMixin):
    """See [documentation for this endpoint](https://developer.osf.io/#operation/institutions_users_list).
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
        return institution.get_institution_users()

    # overrides RetrieveAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()


class InstitutionAuth(JSONAPIBaseView, generics.CreateAPIView):
    """A dedicated view for institution auth, a.k.a "login through institutions".

    This view is only used and should only be used by CAS.  Changing it may break the institution
    login feature.  Please check with @longze and @matt before making any changes.

    CAS makes POST request with JWE/JWT encrypted payload to check with OSF on the identity of users
    authenticated by external institutions.  OSF either finds the matching user or otherwise creates
    a new one.  Everything happens in the API authentication class and the ``post()`` simply returns
    a 204 if the auth passes. (See ``api.institutions.authenticationInstitutionAuthentication``)
    """
    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
    )

    serializer_class = JSONAPISerializer

    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.NULL]
    authentication_classes = (InstitutionAuthentication,)
    view_category = 'institutions'
    view_name = 'institution-auth'

    def post(self, request, *args, **kwargs):
        return Response(status=status.HTTP_204_NO_CONTENT)


class InstitutionRegistrationList(InstitutionNodeList):
    """See [documentation for this endpoint](https://developer.osf.io/#operation/institutions_registration_list).
    """
    serializer_class = RegistrationSerializer
    view_name = 'institution-registrations'

    ordering = ('-modified',)

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
        UserIsAffiliated,
    )
    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ, CoreScopes.INSTITUTION_READ]
    required_write_scopes = [CoreScopes.NODE_REGISTRATIONS_WRITE]
    serializer_class = InstitutionRegistrationsRelationshipSerializer
    parser_classes = (JSONAPIRelationshipParser, JSONAPIRelationshipParserForRegularJSON)

    view_category = 'institutions'
    view_name = 'institution-relationships-registrations'

    def get_object(self):
        inst = self.get_institution()
        auth = get_user_auth(self.request)
        registrations = inst.nodes.filter(is_deleted=False, type='osf.registration').can_view(user=auth.user, private_link=auth.private_link)
        ret = {
            'data': registrations,
            'self': inst,
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
                raise exceptions.PermissionDenied(detail=f'Write permission on registration {id_} required')
            registrations.append(registration)

        for registration in registrations:
            registration.remove_affiliated_institution(inst=instance['self'], user=user)
            registration.save()

    def create(self, *args, **kwargs):
        try:
            ret = super().create(*args, **kwargs)
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
        UserIsAffiliated,
    )
    required_read_scopes = [CoreScopes.NODE_BASE_READ, CoreScopes.INSTITUTION_READ]
    required_write_scopes = [CoreScopes.NODE_BASE_WRITE]
    serializer_class = InstitutionNodesRelationshipSerializer
    parser_classes = (JSONAPIRelationshipParser, JSONAPIRelationshipParserForRegularJSON)

    view_category = 'institutions'
    view_name = 'institution-relationships-nodes'

    def get_object(self):
        inst = self.get_institution()
        auth = get_user_auth(self.request)
        nodes = inst.nodes.filter(is_deleted=False, type='osf.node').can_view(user=auth.user, private_link=auth.private_link)
        ret = {
            'data': nodes,
            'self': inst,
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
                raise exceptions.PermissionDenied(detail=f'Write permission on node {id_} required')
            nodes.append(node)

        for node in nodes:
            node.remove_affiliated_institution(inst=instance['self'], user=user)
            node.save()

    def create(self, *args, **kwargs):
        try:
            ret = super().create(*args, **kwargs)
        except RelationshipPostMakesNoChanges:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return ret


class InstitutionDepartmentList(InstitutionMixin, ElasticsearchListView):
    view_category = 'institutions'
    view_name = 'institution-department-metrics'

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        IsInstitutionalMetricsUser,
    )
    required_read_scopes = [CoreScopes.INSTITUTION_METRICS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = InstitutionDepartmentMetricsSerializer
    renderer_classes = (
        *api_settings.DEFAULT_RENDERER_CLASSES,
        MetricsReportsCsvRenderer,
        MetricsReportsTsvRenderer,
        MetricsReportsJsonRenderer,
    )
    pagination_class = JSONAPINoPagination

    def get_default_search(self):
        _base_search = (
            InstitutionalUserReport.search()
            .filter('term', institution_id=self.get_institution()._id)
        )
        _yearmonth = InstitutionalUserReport.most_recent_yearmonth(base_search=_base_search)
        if _yearmonth is None:
            return None
        _search = (
            _base_search
            .filter('term', report_yearmonth=str(_yearmonth))
            .exclude('term', user_name='Deleted user')
        )
        # add aggregation on department name
        _search.aggs.bucket(
            'agg_departments',
            'terms',
            field='department_name',
            missing=settings.DEFAULT_ES_NULL_VALUE,
            size=settings.MAX_SIZE_OF_ES_QUERY,
        )
        return _search

    def get_queryset(self):
        # execute the search and return a list from the aggregation on department name
        _search = super().get_queryset()
        if not _search:
            return []
        _results = _search[0:0].execute()
        return [
            {'name': _bucket['key'], 'number_of_users': _bucket['doc_count']}
            for _bucket in _results.aggregations['agg_departments'].buckets
        ]


class InstitutionUserMetricsList(InstitutionMixin, ElasticsearchListView):
    '''list view for institution-users metrics
    '''
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        IsInstitutionalMetricsUser,
    )

    required_read_scopes = [CoreScopes.INSTITUTION_METRICS_READ]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'institutions'
    view_name = 'institution-user-metrics'
    renderer_classes = (
        *api_settings.DEFAULT_RENDERER_CLASSES,
        MetricsReportsCsvRenderer,
        MetricsReportsTsvRenderer,
        MetricsReportsJsonRenderer,
    )

    serializer_class = InstitutionUserMetricsSerializer

    default_ordering = '-storage_byte_count'
    ordering_fields = frozenset((
        'user_name',
        'department',
        'month_last_login',
        'month_last_active',
        'account_creation_date',
        'public_projects',
        'private_projects',
        'public_registration_count',
        'embargoed_registration_count',
        'published_preprint_count',
        'public_file_count',
        'storage_byte_count',
    ))

    def get_default_search(self):
        base_search = InstitutionalUserReport.search().filter(
            'term',
            institution_id=self.get_institution()._id,
        )
        yearmonth = InstitutionalUserReport.most_recent_yearmonth(base_search=base_search)
        if yearmonth is None:
            return None

        return (
            base_search
            .filter('term', report_yearmonth=str(yearmonth))
            .exclude('term', user_name='Deleted user')
        )


class InstitutionSummaryMetricsDetail(JSONAPIBaseView, generics.RetrieveAPIView, InstitutionMixin):
    '''detail view for institution-summary metrics
    '''
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        IsInstitutionalMetricsUser,
    )

    required_read_scopes = [CoreScopes.INSTITUTION_METRICS_READ]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'institutions'
    view_name = 'institution-summary-metrics'

    serializer_class = InstitutionSummaryMetricsSerializer

    def get_object(self):
        institution = self.get_institution()
        search_object = self.get_default_search()
        if search_object:
            object = search_object.execute()[0]
            object.id = institution._id
            return object

    def get_default_search(self):
        base_search = InstitutionMonthlySummaryReport.search().filter(
            'term',
            institution_id=self.get_institution()._id,
        )
        yearmonth = InstitutionMonthlySummaryReport.most_recent_yearmonth(base_search=base_search)
        if report_date_str := self.request.query_params.get('report_yearmonth'):
            try:
                yearmonth = YearMonth.from_str(report_date_str)
            except ValueError:
                pass

        if yearmonth is None:
            return None

        return base_search.filter(
            'term',
            report_yearmonth=str(yearmonth),
        )
