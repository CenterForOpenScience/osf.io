import re
import json
import logging
from enum import Enum

from django.http import JsonResponse, HttpResponse, Http404
from elasticsearch8.exceptions import ApiError as Es8ApiError
from elasticsearch_metrics.registry import djelme_registry

from framework.auth.oauth_scopes import CoreScopes

from rest_framework import permissions as drf_permissions
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from rest_framework.settings import api_settings as drf_api_settings

from api.base.elasticsearch_dsl_views import ElasticsearchListView
from api.base.views import JSONAPIBaseView
from api.base.permissions import TokenHasScope
from api.base.waffle_decorators import require_switch
from api.metrics.permissions import (
    IsRawMetricsUser,
    IsRegistriesModerationMetricsUser,
)
from api.metrics.renderers import (
    MetricsReportsCsvRenderer,
    MetricsReportsTsvRenderer,
)
from api.metrics.serializers import (
    RawMetricsSerializer,
    CyclicReportSerializer,
    ReportNameSerializer,
    NodeAnalyticsSerializer,
    UserVisitsSerializer,
    UniqueUserVisitsSerializer,
    CountedAuthUsageSerializer,
)
from api.metrics.utils import (
    parse_date_range,
    should_skip_counted_usage,
)
from api.nodes.permissions import MustBePublic

from osf.features import ENABLE_RAW_METRICS
from osf.metrics.events import (
    OsfCountedUsageEvent,
    RegistriesModerationEvent,
)
from osf.metrics.daily_reports import (
    BaseDailyReport,
    DailyDownloadCountReport,
    DailyInstitutionSummaryReport,
    DailyNodeSummaryReport,
    DailyOsfstorageFileCountReport,
    DailyPreprintSummaryReport,
    DailyStorageAddonUsageReport,
    DailyUserSummaryReport,
    DailyNewUserDomainReport,
)
from osf.metrics.monthly_reports import (
    BaseMonthlyReport,
    MonthlySpamSummaryReport,
)
from osf.metrics.openapi import get_metrics_openapi_json_dict
from osf.models import AbstractNode
from osf.utils.workflows import RegistrationModerationTriggers, RegistrationModerationStates


logger = logging.getLogger(__name__)


VIEWABLE_REPORTS = {
    'download_count': DailyDownloadCountReport,
    'institution_summary': DailyInstitutionSummaryReport,
    'node_summary': DailyNodeSummaryReport,
    'osfstorage_file_count': DailyOsfstorageFileCountReport,
    'preprint_summary': DailyPreprintSummaryReport,
    'storage_addon_usage': DailyStorageAddonUsageReport,
    'user_summary': DailyUserSummaryReport,
    'spam_summary': MonthlySpamSummaryReport,
    'new_user_domains': DailyNewUserDomainReport,
}


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
    def get(self, request, *args, djelme_backend_name, url_path, **kwargs):
        return self._do_es_request(
            request,
            djelme_backend_name,
            method='GET',
            path=url_path,
        )

    @require_switch(ENABLE_RAW_METRICS)
    def post(self, request, *args, djelme_backend_name, url_path, **kwargs):
        return self._do_es_request(
            request,
            djelme_backend_name,
            method='POST',
            path=url_path,
        )

    @require_switch(ENABLE_RAW_METRICS)
    def put(self, request, *args, djelme_backend_name, url_path, **kwargs):
        return self._do_es_request(
            request,
            djelme_backend_name,
            method='PUT',
            path=url_path,
        )

    def _do_es_request(self, django_request, djelme_backend_name, method, path):
        _client = self._get_es_client(djelme_backend_name)
        _body = (
            json.loads(django_request.body)
            if django_request.body else None
        )
        _content_type = django_request.headers.get('Content-Type')
        _headers = (
            {'Content-Type': _content_type, 'Accept': 'application/json'}
            if _content_type else None
        )
        try:
            _response = _client.perform_request(
                method,
                f'/{path}',
                params=django_request.GET.dict(),
                body=_body,
                headers=_headers,
            )
        except Es8ApiError as _api_error:
            return HttpResponse(
                str(_api_error),
                content_type='text/plain; charset=utf-8',
                status=_api_error.status_code,
            )
        return JsonResponse(_response.body)

    def _get_es_client(self, djelme_backend_name):
        try:
            _backend = djelme_registry.get_backend(djelme_backend_name)
        except LookupError:
            raise Http404
        return _backend.elastic_client


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
        _search = RegistriesModerationEvent.search().update_from_dict(self._build_es_query())
        _search_response = _search.execute()
        _providers_agg_json = (
            _search_response.aggregations['providers'].to_dict()
            if _search_response.aggregations
            else {}
        )
        return JsonResponse(_providers_agg_json)

    def _build_es_query(self):
        _submit_trigger = RegistrationModerationTriggers.SUBMIT.db_name
        _reject_trigger = RegistrationModerationTriggers.REJECT_SUBMISSION.db_name
        _accept_withdrawal_trigger = RegistrationModerationTriggers.ACCEPT_WITHDRAWAL.db_name
        _accepted_state = RegistrationModerationStates.ACCEPTED.db_name
        _embargo_state = RegistrationModerationStates.EMBARGO.db_name
        _rejected_state = RegistrationModerationStates.REJECTED.db_name
        _withdrawn_state = RegistrationModerationStates.WITHDRAWN.db_name
        return {
            'aggs': {
                'providers': {
                    'terms': {'field': 'provider_id'},
                    'aggs': {
                        'transitions_without_comments': {
                            'missing': {'field': 'comment'},
                        },
                        'transitions_with_comments': {
                            'filter': {'exists': {'field': 'comment'}},
                        },
                        'submissions': {
                            'filter': {'term': {'trigger': _submit_trigger}},
                        },
                        'accepted_with_embargo': {
                            'filter': {
                                'bool': {
                                    'must': [
                                        {'term': {'to_state': _embargo_state}},
                                        {'term': {'trigger': _submit_trigger}},
                                    ],
                                },
                            },
                        },
                        'accepted_without_embargo': {
                            'filter': {
                                'bool': {
                                    'must': [
                                        {'term': {'to_state': _accepted_state}},
                                        {'term': {'trigger': _submit_trigger}},
                                    ],
                                },
                            },
                        },
                        'rejected': {
                            'filter': {
                                'bool': {
                                    'must': [
                                        {'term': {'to_state': _rejected_state}},
                                        {'term': {'trigger': _reject_trigger}},
                                    ],
                                },
                            },
                        },
                        'withdrawn': {
                            'filter': {
                                'bool': {
                                    'must': [
                                        {'term': {'to_state': _withdrawn_state}},
                                        {'term': {'trigger': _accept_withdrawal_trigger}},
                                    ],
                                },
                            },
                        },
                    },
                },
            },
        }


###
# reports

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
        return Response({'data': serializer.data})


class ReportList(ElasticsearchListView):
    view_category = 'metrics'
    view_name = 'report-list'

    permission_classes = (
        TokenHasScope,
        drf_permissions.IsAuthenticatedOrReadOnly,
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = CyclicReportSerializer
    renderer_classes = (
        *drf_api_settings.DEFAULT_RENDERER_CLASSES,
        *ElasticsearchListView.FILE_RENDERER_CLASSES,
    )

    default_ordering = '-cycle_coverage'
    ordering_fields = frozenset((
        'cycle_coverage',
    ))

    def get_default_search(self):
        _report_name = self.kwargs['report_name']
        try:
            _report_cls = VIEWABLE_REPORTS[_report_name]
        except KeyError:
            return Response(
                {
                    'errors': [{
                        'title': 'unknown report name',
                        'detail': f'unknown report: "{_report_name}"',
                    }],
                },
                status=404,
            )
        return _report_cls.search()

    def get_serializer_context(self):
        return {
            **super().get_serializer_context(),
            'report_name': self.kwargs['report_name'],
        }

class RecentReportList(JSONAPIBaseView):
    MAX_COUNT = 10000
    DEFAULT_DAYS_BACK = 13

    permission_classes = (
        TokenHasScope,
        drf_permissions.IsAuthenticatedOrReadOnly,
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'metrics'
    view_name = 'recent-report-list'

    serializer_class = CyclicReportSerializer
    renderer_classes = (
        *drf_api_settings.DEFAULT_RENDERER_CLASSES,
        MetricsReportsCsvRenderer,
        MetricsReportsTsvRenderer,
    )

    def get(self, request, *args, report_name):
        try:
            report_class = VIEWABLE_REPORTS[report_name]
        except KeyError:
            return Response(
                {
                    'errors': [{
                        'title': 'unknown report name',
                        'detail': f'unknown report: "{report_name}"',
                    }],
                },
                status=404,
            )
        is_daily = issubclass(report_class, BaseDailyReport)
        days_back = request.GET.get('days_back', self.DEFAULT_DAYS_BACK if is_daily else None)
        is_monthly = issubclass(report_class, BaseMonthlyReport)

        range_filter = parse_date_range(request.GET, is_monthly=is_monthly)
        search_recent = (
            report_class.search()
            .filter('range', cycle_coverage=range_filter)
            .sort('-cycle_coverage')
            [:self.MAX_COUNT]
        )
        if days_back:
            search_recent.filter('range', report_date={'gte': f'now/d-{days_back}d'})

        report_date_range = parse_date_range(request.GET)
        search_response = search_recent.execute()
        serializer = self.serializer_class(
            search_response,
            many=True,
            context={'report_name': report_name},
        )
        accepted_format = request.accepted_renderer.format
        response_headers = {}
        if accepted_format in ('tsv', 'csv'):
            from_date = report_date_range['gte']
            until_date = report_date_range['lte']
            filename = (
                f'{report_name}__'
                f'until_{until_date}__'
                f'from_{from_date}.{accepted_format}'
            )
            response_headers['Content-Disposition'] = f'attachment; filename={filename}'
        return Response(
            {'data': serializer.data},
            headers=response_headers,
        )


class CountedAuthUsageView(JSONAPIBaseView):
    view_category = 'metrics'
    view_name = 'counted-usage'

    serializer_class = CountedAuthUsageSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data,
            context={
                'user_id': request.user._id if request.user.is_authenticated else None,
                'request_host': request.get_host(),
                'request_useragent': request.META.get('HTTP_USER_AGENT', ''),
            },
        )
        serializer.is_valid(raise_exception=True)
        if should_skip_counted_usage(
            request.user,
            item_guid=serializer.validated_data.get('item_guid'),
            pageview_info=serializer.validated_data.get('pageview_info'),
        ):
            return HttpResponse(status=204)
        serializer.save()
        return HttpResponse(status=201)


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
        analytics_result = self._run_node_analytics_query(node.get_semantic_iri(), timespan)
        serializer = self.serializer_class(
            analytics_result,
            context={
                'node_guid': node_guid,
                'timespan': timespan,
            },
        )
        return Response({'data': serializer.data})

    def _run_node_analytics_query(self, item_iri, timespan):
        query_dict = self._build_query_payload(item_iri, NodeAnalyticsQuery.Timespan(timespan))
        analytics_search = OsfCountedUsageEvent.search().update_from_dict(query_dict)
        return analytics_search.execute()

    def _build_query_payload(self, item_iri, timespan):
        return {
            'size': 0,  # don't return hits, just the aggregations
            'query': {
                'bool': {
                    'filter': [
                        {'term': {'within_iris': item_iri}},
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
                        'calendar_interval': 'day',
                    },
                    'aggs': {
                        'unique-count': {
                            'cardinality': {'field': 'sessionhour_id'},
                        },
                    },
                },
                'time-of-day': {
                    'terms': {
                        'field': 'pageview_info.hour_of_day',
                        'size': 24,
                    },
                    'aggs': {
                        'unique-count': {
                            'cardinality': {'field': 'sessionhour_id'},
                        },
                    },
                },
                'referer-domain': {
                    'terms': {
                        'field': 'pageview_info.referer_domain',
                        'size': 10,
                    },
                    'aggs': {
                        'unique-count': {
                            'cardinality': {'field': 'sessionhour_id'},
                        },
                    },
                },
                'popular-pages': {
                    'terms': {
                        'field': 'pageview_info.page_path',
                        'size': 10,
                    },
                    'aggs': {
                        'unique-count': {
                            'cardinality': {'field': 'sessionhour_id'},
                        },
                        'route-for-path': {
                            'terms': {
                                'field': 'pageview_info.route_name',
                                'size': 1,
                            },
                        },
                        'title-for-path': {
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


class UserVisitsQuery(JSONAPIBaseView):
    permission_classes = (
        MustBePublic,
        TokenHasScope,
        drf_permissions.IsAuthenticatedOrReadOnly,
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'metrics'
    view_name = 'user-visits-query'

    serializer_class = UserVisitsSerializer

    DAYS_PER_PERIOD = {'day': 1, 'month': 31, 'year': 365}

    def get(self, request, *args):
        report_date = {'gte': 'now/d-1d'}

        if request.GET.get('timeframe', False):
            timeframe = request.GET.get('timeframe')
            if timeframe is not None:
                m = re.match(r'previous_(\d+)_(day|month|year)s?', timeframe)
                if m:
                    period_count = m.group(1)
                    period = m.group(2)
                    days_back = int(period_count) * self.DAYS_PER_PERIOD[period]
                else:
                    raise Exception(f'Unsupported timeframe format: "{timeframe}"')
                report_date = {'gte': f'now/d-{days_back}d'}
        elif request.GET.get('timeframeStart'):
            tsStart = request.GET.get('timeframeStart')
            tsEnd = request.GET.get('timeframeEnd')
            report_date = {'gte': tsStart, 'lt': tsEnd}
        else:
            pass  # just fall back to days_back for now

        timespan = report_date
        analytics_result = self._run_user_visits_query(timespan)
        serializer = self.serializer_class(
            analytics_result,
            context={
                'timespan': timespan,
            },
        )
        return JsonResponse({'data': serializer.data})

    def _run_user_visits_query(self, timespan):
        query_dict = self._build_query_payload(timespan)
        analytics_search = OsfCountedUsageEvent.search().update_from_dict(query_dict)
        return analytics_search.execute()

    def _build_query_payload(self, timespan):
        return {
            'size': 0,  # don't return hits, just the aggregations
            'query': {
                'bool': {
                    'filter': [
                        {'range': {'timestamp': timespan}},
                    ],
                },
            },
            'aggs': {
                'unique-visits': {
                    'date_histogram': {
                        'field': 'timestamp',
                        'calendar_interval': 'day',
                    },
                    'aggs': {
                        'user-visits': {
                            'cardinality': {'field': 'sessionhour_id'},
                        },
                    },
                },
            },
        }


class UniqueUserVisitsQuery(UserVisitsQuery):
    view_name = 'unique-user-visits-query'

    serializer_class = UniqueUserVisitsSerializer

    def _build_query_payload(self, timespan):
        payload = super()._build_query_payload(timespan)
        payload['query']['bool']['filter'].insert(0, {'term': {'user_is_authenticated': True}})
        return payload


class MetricsOpenapiView(GenericAPIView):
    permission_classes = (
        TokenHasScope,
        drf_permissions.IsAuthenticatedOrReadOnly,
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'metrics'
    view_name = 'openapi-json'

    def get(self, request):
        _openapi_json = get_metrics_openapi_json_dict(reports=VIEWABLE_REPORTS)
        return JsonResponse(
            _openapi_json,
            json_dumps_params={'indent': 2},
            headers={
                'Cache-Control': f'immutable, public, max-age={60 * 60 * 24 * 7}',  # pls cache for a week
            },
        )
