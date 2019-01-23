import re
from datetime import timedelta

import waffle
from django.utils import timezone

from api.base.exceptions import InvalidQueryStringError
from osf import features


class MetricsViewMixin(object):
    """Mixin for views that expose metrics via django-elasticsearch-metrics.
    Enables metrics to be requested with a query parameter, like so: ::

        /v2/myview?metrics[downloads]=monthly

    Any subclass of this mixin MUST do the following:

    * Use a serializer_class that subclasses MetricsSerializerMixin
    * Define metric_map as a class variable. It should be dict mapping metric name
    ("downloads") to a Metric class (PreprintDownload)
    * For list views: implement `get_annotated_queryset_with_metrics`
    * For detail views: implement `add_metric_to_object`
    """
    # Adapted from FilterMixin.QUERY_PATTERN
    METRICS_QUERY_PATTERN = re.compile(r'^metrics\[(?P<metric_name>((?:,*\s*\w+)*))\]$')
    TIMEDELTA_MAP = {
        'daily': timedelta(hours=24),
        'weekly': timedelta(days=7),
        'monthly': timedelta(days=30),
        'yearly': timedelta(days=365),
    }
    VALID_METRIC_PERIODS = {
        'daily',
        'weekly',
        'monthly',
        'yearly',
        'total',
    }

    @property
    def metric_map(self):
        raise NotImplementedError('MetricsViewMixin sublcasses must define a metric_map class variable.')

    def get_annotated_queryset_with_metrics(self, queryset, metric_class, metric_name, after):
        """Return a queryset annotated with metrics. Use for list endpoints that expose metrics."""
        raise NotImplementedError('MetricsViewMixin subclasses must define get_annotated_queryset_with_metrics().')

    def add_metric_to_object(self, obj, metric_class, metric_name, after):
        """Set an attribute for a metric on obj. Use for detail endpoints that expose metrics.
        Return the modified object.
        """
        raise NotImplementedError('MetricsViewMixin subclasses must define add_metric_to_object().')

    @property
    def metrics_requested(self):
        return (
            waffle.switch_is_active(features.ELASTICSEARCH_METRICS) and
            bool(self.parse_metric_query_params(self.request.query_params))
        )

    # Adapted from FilterMixin.parse_query_params
    # TODO: Should we get rid of query_params argument and use self.request.query_params instead?
    def parse_metric_query_params(self, query_params):
        """Parses query parameters to a dict usable for fetching metrics.

        :param dict query_params:
        :return dict of the format {
            <metric_name>: {
                'period': <[daily|weekly|monthly|yearly|total]>,
            }
        }
        """
        query = {}
        for key, value in query_params.iteritems():
            match = self.METRICS_QUERY_PATTERN.match(key)
            if match:
                match_dict = match.groupdict()
                metric_name = match_dict['metric_name']
                query[metric_name] = value
        return query

    def _add_metrics(self, queryset_or_obj, method):
        """Parse the ?metric[METRIC]=PERIOD query param, validate it, and
        run ``method`` for each each requested object.

        This is used to share code between add_metric_to_object and get_metrics_queryset.
        """
        metrics_requested = self.parse_metric_query_params(self.request.query_params)
        if metrics_requested:
            metric_map = self.metric_map
            for metric, period in metrics_requested.items():
                if metric not in metric_map:
                    raise InvalidQueryStringError("Invalid metric in query string: '{}'".format(metric), parameter='metrics')
                if period not in self.VALID_METRIC_PERIODS:
                    raise InvalidQueryStringError("Invalid period for metric: '{}'".format(period), parameter='metrics')
                metric_class = metric_map[metric]
                if period == 'total':
                    after = None
                else:
                    after = timezone.now() - self.TIMEDELTA_MAP[period]
                queryset_or_obj = method(queryset_or_obj, metric_class, metric, after)
        return queryset_or_obj

    def add_metrics_to_object(self, obj):
        """Helper method used for detail views."""
        return self._add_metrics(obj, method=self.add_metric_to_object)

    def get_metrics_queryset(self, queryset):
        """Helper method used for list views."""
        return self._add_metrics(queryset, method=self.get_annotated_queryset_with_metrics)

    # Override get_default_queryset for convenience
    def get_default_queryset(self):
        queryset = super(MetricsViewMixin, self).get_default_queryset()
        return self.get_metrics_queryset(queryset)

class MetricsSerializerMixin(object):
    @property
    def available_metrics(self):
        raise NotImplementedError(
            'MetricSerializerMixin subclasses must define an available_metrics (set) class variable.',
        )

    # Override JSONAPISerializer
    def get_meta(self, obj):
        meta = super(MetricsSerializerMixin, self).get_meta(obj)
        for metric in self.available_metrics:
            if hasattr(obj, metric):
                meta = meta or {'metrics': {}}
                meta['metrics'][metric] = getattr(obj, metric)
        return meta
