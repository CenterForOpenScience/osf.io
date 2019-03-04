from datetime import timedelta, datetime

import pytz
from django.utils import timezone
from django.http import JsonResponse
from rest_framework.exceptions import ValidationError
from rest_framework import permissions as drf_permissions
from elasticsearch.exceptions import NotFoundError, RequestError

from osf.models import Preprint
from framework.auth.oauth_scopes import CoreScopes
from api.base.permissions import TokenHasScope
from osf.metrics import PreprintDownload, PreprintView
from api.metrics.permissions import IsPreprintMetricsUser
from api.metrics.serializers import PreprintMetricSerializer
from api.base.views import JSONAPIBaseView


class PreprintMetricMixin(JSONAPIBaseView):
    permission_classes = (
        drf_permissions.IsAuthenticated,
        drf_permissions.IsAdminUser,
        IsPreprintMetricsUser,
        TokenHasScope,
    )

    required_read_scopes = [CoreScopes.METRICS_READ]
    required_write_scopes = [CoreScopes.METRICS_WRITE]

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
            raise ValidationError('You must provide one or more preprint guids to gather metrics for')
        preprint_guids = preprint_guid_string.split(',')
        for guid in preprint_guids:
            preprint = Preprint.load(guid)
            if not preprint:
                raise ValidationError('One or more of the preprint guids you supplied was not for a valid preprint.')

        return search.filter('terms', preprint_id=preprint_guids)

    def format_response(self, response, query_params):
        data = []
        if getattr(response, 'aggregations') and response.aggregations:
            for result in response.aggregations.preprints_per_day.buckets:
                guid_results = {}
                for preprint_result in result.per_preprint.buckets:
                    guid_results[preprint_result['key']] = preprint_result['doc_count']
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

    def parse_datetimes(self, query_params):
        now = timezone.now()
        date_format = '%Y-%m-%d'
        datetime_format = '%Y-%m-%dT%H:%M'
        default_days_back = 5

        on_date = query_params.get('on_date', None)
        start_datetime = query_params.get('start_datetime')
        end_datetime = query_params.get('end_datetime')

        using_time = False
        if (start_datetime and 'T' in start_datetime) or (end_datetime and 'T' in end_datetime):
            using_time = True

        # error if both on_date and a date range
        if on_date and (start_datetime or end_datetime):
            raise ValidationError('You cannot provide both an on date and an end or start datetime.')

        # error if a time is used for a specific date request
        if on_date and 'T' in on_date:
            raise ValidationError('You cannot provide a time for an on_date request.')

        # error if an end_datetime is provided without a start_datetime
        if end_datetime and not start_datetime:
            raise ValidationError('You cannot provide a specific end_datetime with no start_datetime')

        if on_date:
            start_datetime = datetime.strptime(on_date, date_format)
            end_datetime = start_datetime.replace(hour=23, minute=59, second=59, microsecond=999)

        else:
            # default date range: 6 days ago to 1 day ago, at midnight
            default_start = (now - timedelta(default_days_back + 1)).replace(hour=0, minute=0, second=0, microsecond=0)
            default_end = (now - timedelta(1)).replace(hour=23, minute=59, second=59, microsecond=999)

            format_to_use = datetime_format if using_time else date_format
            try:
                start_datetime = datetime.strptime(start_datetime, format_to_use).replace(tzinfo=pytz.utc) if start_datetime else default_start
                end_datetime = datetime.strptime(end_datetime, format_to_use).replace(tzinfo=pytz.utc) if end_datetime else default_end
            except ValueError:
                raise ValidationError('You cannot use a mixture of date format and datetime format.')
            # if not using time, make sure to ensure start date is at midnight, and end_date is 11:59
            if not using_time:
                start_datetime = start_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
                end_datetime = end_datetime.replace(hour=23, minute=59, second=59, microsecond=999)

        if start_datetime > end_datetime:
            raise ValidationError('The end_datetime must be after the start_datetime')

        return start_datetime, end_datetime

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

        start_datetime, end_datetime = self.parse_datetimes(query_params)

        search = self.metric.search(after=start_datetime)
        search = search.filter('range', timestamp={'gte': start_datetime, 'lt': end_datetime})
        search.aggs.bucket('preprints_per_day', 'date_histogram', field='timestamp', interval=interval)
        search.aggs['preprints_per_day'].metric('per_preprint', 'terms', field='preprint_id.keyword')
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
        search = search.update_from_dict(query)
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
