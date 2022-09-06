import json
from enum import Enum

from django.http import JsonResponse, HttpResponse, Http404
from django.utils import timezone
from elasticsearch.exceptions import NotFoundError, RequestError
from elasticsearch_dsl.connections import get_connection
from rest_framework.exceptions import ValidationError
from rest_framework import permissions as drf_permissions
from rest_framework.generics import GenericAPIView

from framework.auth.oauth_scopes import CoreScopes
from api.base.permissions import TokenHasScope
from api.metrics.permissions import IsPreprintMetricsUser, IsRawMetricsUser, IsRegistriesModerationMetricsUser
from api.metrics.serializers import (
    PreprintMetricSerializer,
    RawMetricsSerializer,
    CountedUsageSerializer,
    DailyReportSerializer,
    ReportNameSerializer,
    NodeAnalyticsSerializer,
)
from api.metrics.utils import parse_datetimes
from api.base.views import JSONAPIBaseView
from api.base.waffle_decorators import require_switch
from api.nodes.permissions import MustBePublic
from osf.features import ENABLE_RAW_METRICS
from osf.metrics import PreprintDownload, PreprintView, RegistriesModerationMetrics, CountedUsageV1
from osf.metrics import reports
from osf.metrics.utils import stable_key
from osf.models import AbstractNode


class PreprintMetricMixin(JSONAPIBaseView):
    permission_classes = (
        drf_permissions.IsAuthenticated,
        drf_permissions.IsAdminUser,
        IsPreprintMetricsUser,
        TokenHasScope,
    )

    required_read_scopes = [CoreScopes.METRICS_BASIC]
    required_write_scopes = [CoreScopes.METRICS_RESTRICTED]

    serializer_class = PreprintMetricSerializer

    @property
    def metric_type(self):
        raise NotImplementedError

    @property
    def metric(self):
        raise NotImplementedError

    def add_search(self, search, query_params, **kwargs):
        """
        get list of guids from the kwargs
        use that in a query to narrow down metrics results
        """
        preprint_guid_string = query_params.get('guids')
        if not preprint_guid_string:
            raise ValidationError(
                'To gather metrics for preprints, you must provide one or more preprint ' +
                'guids in the `guids` query parameter.',
            )
        preprint_guids = preprint_guid_string.split(',')

        return search.filter('terms', preprint_id=preprint_guids)

    def format_response(self, response, query_params):
        data = []
        if getattr(response, 'aggregations') and response.aggregations:
            for result in response.aggregations.dates.buckets:
                guid_results = {}
                for preprint_result in result.preprints.buckets:
                    guid_results[preprint_result['key']] = preprint_result['total']['value']
                    # return 0 for the guids with no results for consistent payloads
                guids = query_params['guids'].split(',')
                if guid_results.keys() != guids:
                    for guid in guids:
                        if not guid_results.get(guid):
                            guid_results[guid] = 0
                result_dict = {result.key_as_string: guid_results}
                data.append(result_dict)

        return {
            'metric_type': self.metric_type,
            'data': data,
        }

    def execute_search(self, search, query=None):
        try:
            # There's a bug in the ES python library the prevents us from updating the search object, so lets just make
            # the raw query. If we have it.
            if query:
                es = get_connection(search._using)
                response = search._response_class(
                    search,
                    es.search(
                        index=search._index,
                        body=query,
                    ),
                )
            else:
                response = search.execute()
        except NotFoundError:
            # _get_relevant_indices returned 1 or more indices
            # that doesn't exist. Fall back to unoptimized query
            search = search.index().index(self.metric._default_index())
            response = search.execute()
        return response

    def get(self, *args, **kwargs):
        query_params = getattr(self.request, 'query_params', self.request.GET)

        interval = query_params.get('interval', 'day')

        start_datetime, end_datetime = parse_datetimes(query_params)

        search = self.metric.search(after=start_datetime)
        search = search.filter('range', timestamp={'gte': start_datetime, 'lt': end_datetime})
        search.aggs.bucket('dates', 'date_histogram', field='timestamp', interval=interval) \
            .bucket('preprints', 'terms', field='preprint_id') \
            .metric('total', 'sum', field='count')
        search = self.add_search(search, query_params, **kwargs)
        response = self.execute_search(search)
        resp_dict = self.format_response(response, query_params)

        return JsonResponse(resp_dict)

    def post(self, request, *args, **kwargs):
        """
        For a bit of future proofing, accept custom elasticsearch aggregation queries in JSON form.
        Caution - this could be slow if a very large query is executed, so use with care!
        """
        search = self.metric.search()
        query = request.data.get('query')

        try:
            results = self.execute_search(search, query)
        except RequestError as e:
            if e.args:
                raise ValidationError(e.info['error']['root_cause'][0]['reason'])
            raise ValidationError('Malformed elasticsearch query.')

        return JsonResponse(results.to_dict())


class PreprintViewMetrics(PreprintMetricMixin):

    view_category = 'preprint-metrics'
    view_name = 'preprint-view-metrics'

    @property
    def metric_type(self):
        return 'views'

    @property
    def metric(self):
        return PreprintView


class PreprintDownloadMetrics(PreprintMetricMixin):

    view_category = 'preprint-metrics'
    view_name = 'preprint-download-metrics'

    @property
    def metric_type(self):
        return 'downloads'

    @property
    def metric(self):
        return PreprintDownload

class RawMetricsView(GenericAPIView):

    permission_classes = (
        drf_permissions.IsAuthenticated,
        IsRawMetricsUser,
        TokenHasScope,
    )

    required_read_scopes = [CoreScopes.METRICS_BASIC]
    required_write_scopes = [CoreScopes.METRICS_RESTRICTED]

    view_category = 'raw-metrics'
    view_name = 'raw-metrics-view'

    serializer_class = RawMetricsSerializer

    @require_switch(ENABLE_RAW_METRICS)
    def delete(self, request, *args, **kwargs):
        raise ValidationError('DELETE not supported. Use GET/POST/PUT')

    @require_switch(ENABLE_RAW_METRICS)
    def get(self, request, *args, **kwargs):
        connection = get_connection()
        url_path = kwargs['url_path']
        return JsonResponse(connection.transport.perform_request('GET', f'/{url_path}'))

    @require_switch(ENABLE_RAW_METRICS)
    def post(self, request, *args, **kwargs):
        connection = get_connection()
        url_path = kwargs['url_path']
        body = json.loads(request.body)
        return JsonResponse(connection.transport.perform_request('POST', f'/{url_path}', body=body))

    @require_switch(ENABLE_RAW_METRICS)
    def put(self, request, *args, **kwargs):
        connection = get_connection()
        url_path = kwargs['url_path']
        body = json.loads(request.body)
        return JsonResponse(connection.transport.perform_request('PUT', f'/{url_path}', body=body))


class RegistriesModerationMetricsView(GenericAPIView):

    permission_classes = (
        drf_permissions.IsAuthenticated,
        IsRegistriesModerationMetricsUser,
        TokenHasScope,
    )

    required_read_scopes = [CoreScopes.METRICS_BASIC]
    required_write_scopes = [CoreScopes.METRICS_RESTRICTED]

    view_category = 'raw-metrics'
    view_name = 'raw-metrics-view'

    def get(self, request, *args, **kwargs):
        return JsonResponse(RegistriesModerationMetrics.get_registries_info())


VIEWABLE_REPORTS = {
    'addon_usage': reports.AddonUsageReportV0,
    'download_count': reports.DownloadCountReportV0,
    'institution_summary': reports.InstitutionSummaryReportV0,
    'node_summary': reports.NodeSummaryReportV0,
    'osfstorage_file_count': reports.OsfstorageFileCountReportV0,
    'preprint_summary': reports.PreprintSummaryReportV0,
    'user_summary': reports.UserSummaryReportV0,
}


class ReportNameList(JSONAPIBaseView):
    permission_classes = (
        TokenHasScope,
        drf_permissions.IsAuthenticatedOrReadOnly,
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'metrics'
    view_name = 'report-name-list'

    serializer_class = ReportNameSerializer

    def get(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            VIEWABLE_REPORTS.keys(),
            many=True,
        )
        return JsonResponse({'data': serializer.data})


class LatestReportDetail(JSONAPIBaseView):
    permission_classes = (
        TokenHasScope,
        drf_permissions.IsAuthenticatedOrReadOnly,
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'metrics'
    view_name = 'latest-report-detail'

    serializer_class = DailyReportSerializer

    def get(self, request, *args, report_name):
        try:
            report_class = VIEWABLE_REPORTS[report_name]
        except KeyError:
            return JsonResponse(
                {'errors': [{
                    'title': 'unknown report name',
                    'detail': f'unknown report: "{report_name}"',
                }]},
                status=404,
            )

        latest_search = (
            report_class.search()
            .sort('-report_date', '-timestamp')
            [0]
        )

        search_response = latest_search.execute()
        if not search_response.hits:
            return JsonResponse(
                {'errors': [{
                    'title': 'no latest report found',
                    'detail': f'no "{report_name}" reports found',
                }]},
                status=404,
            )
        latest_report = search_response.hits[0]

        serializer = self.serializer_class(
            latest_report,
            context={'report_name': report_name},
        )
        return JsonResponse({'data': serializer.data})


class RecentReportList(JSONAPIBaseView):
    MAX_COUNT = 1000
    DEFAULT_DAYS_BACK = 13

    permission_classes = (
        TokenHasScope,
        drf_permissions.IsAuthenticatedOrReadOnly,
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'metrics'
    view_name = 'recent-report-list'

    serializer_class = DailyReportSerializer

    def get(self, request, *args, report_name):
        try:
            report_class = VIEWABLE_REPORTS[report_name]
        except KeyError:
            return JsonResponse(
                {'errors': [{
                    'title': 'unknown report name',
                    'detail': f'unknown report: "{report_name}"',
                }]},
                status=404,
            )

        days_back = request.GET.get('days_back', self.DEFAULT_DAYS_BACK)

        search_recent = (
            report_class.search()
            .filter('range', report_date={'gte': f'now/d-{days_back}d'})
            .sort('-report_date')
            [:self.MAX_COUNT]
        )

        search_response = search_recent.execute()

        serializer = self.serializer_class(
            search_response,
            many=True,
        )
        return JsonResponse({'data': serializer.data})


class CountedUsage(JSONAPIBaseView):
    view_category = 'metrics'
    view_name = 'counted-usage'

    serializer_class = CountedUsageSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        session_id = self._get_session_id(
            request,
            client_session_id=serializer.validated_data.get('client_session_id'),
        )
        serializer.save(session_id=session_id)
        return HttpResponse(status=201)

    def _get_session_id(self, request, client_session_id=None):
        # get a session id as described in the COUNTER code of practice:
        # https://cop5.projectcounter.org/en/5.0.2/07-processing/03-counting-unique-items.html
        # (this is different from the "login session" tracked by `osf.models.Session` (which
        # lasts about a month) but more similar to the "user session" tracked by the
        # 'keenSessionId' cookie (which lasts ~25min))
        now = timezone.now()
        current_date_str = now.date().isoformat()

        if client_session_id:
            session_id_parts = [
                client_session_id,
                current_date_str,
            ]
        elif request.user.is_authenticated:
            session_id_parts = [
                request.user._id,
                current_date_str,
                now.hour,
            ]
        else:
            session_id_parts = [
                request.get_host(),
                request.META.get('HTTP_USER_AGENT', ''),
                current_date_str,
                now.hour,
            ]
        return stable_key(*session_id_parts)


class NodeAnalyticsQuery(JSONAPIBaseView):
    permission_classes = (
        MustBePublic,
        TokenHasScope,
        drf_permissions.IsAuthenticatedOrReadOnly,
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'metrics'
    view_name = 'node-analytics-query'

    serializer_class = NodeAnalyticsSerializer

    class Timespan(Enum):
        WEEK = 'week'
        FORTNIGHT = 'fortnight'
        MONTH = 'month'

    def get(self, request, *args, node_guid, timespan):
        try:
            node = AbstractNode.load(node_guid)
        except AbstractNode.DoesNotExist:
            raise Http404
        self.check_object_permissions(request, node)
        analytics_result = self._run_query(node_guid, timespan)
        serializer = self.serializer_class(
            analytics_result,
            context={
                'node_guid': node_guid,
                'timespan': timespan,
            },
        )
        return JsonResponse({'data': serializer.data})

    def _run_query(self, node_guid, timespan):
        query_dict = self._build_query_payload(node_guid, NodeAnalyticsQuery.Timespan(timespan))
        analytics_search = CountedUsageV1.search().update_from_dict(query_dict)
        return analytics_search.execute()

    def _build_query_payload(self, node_guid, timespan):
        return {
            'size': 0,  # don't return hits, just the aggregations
            'query': {
                'bool': {
                    'filter': [
                        {'term': {'item_guid': node_guid}},
                        {'term': {'item_public': True}},
                        {'term': {'action_labels': 'view'}},
                        {'term': {'action_labels': 'web'}},
                        self._build_timespan_filter(timespan),
                    ],
                },
            },
            'aggs': {
                'unique-visits': {
                    'date_histogram': {
                        'field': 'timestamp',
                        'interval': 'day',
                        'format': 'yyyy-MM-dd',
                    },
                },
                'time-of-day': {
                    'terms': {
                        'field': 'pageview_info.hour_of_day',
                        'size': 24,
                    },
                },
                'referer-domain': {
                    'terms': {
                        'field': 'pageview_info.referer_domain',
                        'size': 10,
                    },
                },
                'popular-pages': {
                    'terms': {
                        'field': 'pageview_info.page_path',
                        'exclude': '.*/project/.*',
                        'size': 10,
                    },
                    'aggs': {
                        'page-titles': {
                            'terms': {
                                'field': 'pageview_info.page_title',
                                'size': 1,
                            },
                        },
                    },
                },
            },
        }

    def _build_timespan_filter(self, timespan):
        if timespan == NodeAnalyticsQuery.Timespan.WEEK:
            from_date = 'now-1w/d'
        elif timespan == NodeAnalyticsQuery.Timespan.FORTNIGHT:
            from_date = 'now-2w/d'
        elif timespan == NodeAnalyticsQuery.Timespan.MONTH:
            from_date = 'now-1M/d'
        else:
            raise NotImplementedError
        return {
            'range': {
                'timestamp': {
                    'gte': from_date,
                },
            },
        }
