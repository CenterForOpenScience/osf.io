from django.http import JsonResponse
from rest_framework.exceptions import ValidationError
from rest_framework import permissions as drf_permissions
from elasticsearch.exceptions import NotFoundError, RequestError

from framework.auth.oauth_scopes import CoreScopes
from api.base.permissions import TokenHasScope
from osf.metrics import PreprintDownload, PreprintView
from api.metrics.permissions import IsPreprintMetricsUser
from api.metrics.serializers import PreprintMetricSerializer
from api.metrics.utils import parse_datetimes
from api.base.views import JSONAPIBaseView


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

    def execute_search(self, search):
        # TODO - this is copied from get_count_for_preprint in metrics.py - abstract this out in the future
        try:
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
        try:
            results = self.execute_search(search)
        except RequestError:
            raise ValidationError('Misformed elasticsearch query.')
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
