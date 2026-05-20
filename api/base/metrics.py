import abc
import waffle

from api.base.exceptions import InvalidQueryStringError
from osf import features
from osf.metrics.events import OsfCountedUsageEvent
from osf.metrics.monthly_reports import MonthlyPublicItemUsageReport
from osf.models.base import osfid_iri


class UsageMetricsViewMixin(abc.ABC):
    """Mixin for views that expose metrics via django-elasticsearch-metrics.
    Enables metrics to be requested with a query parameter, like so: ::

        /v2/myview?metrics[downloads]=monthly

    Any subclass of this mixin MUST do the following:

    * Use a serializer_class that subclasses MetricsSerializerMixin
    * Call add_metrics_to_object(obj) to get `views` and/or `downloads`
      assigned on the obj (according to query params)
    """
    METRICS_QUERY_MAP = {
        'metrics[views]': OsfCountedUsageEvent.ActionLabel.VIEW,
        'metrics[downloads]': OsfCountedUsageEvent.ActionLabel.DOWNLOAD,
    }
    METRICS_ATTR_MAP = {
        OsfCountedUsageEvent.ActionLabel.VIEW: 'views',
        OsfCountedUsageEvent.ActionLabel.DOWNLOAD: 'downloads',
    }
    TIMESPAN_MAP = {
        'daily': 'now-1d/d',
        'weekly': 'now-1w/d',
        'monthly': 'now-1M/d',
    }
    VALID_METRIC_PERIODS = {
        'daily',
        'weekly',
        'monthly',
        'total',
    }

    @property
    def metrics_requested(self):
        return (
            waffle.switch_is_active(features.ELASTICSEARCH_METRICS)
            and any(_param in self.METRICS_QUERY_MAP for _param in self.request.query_params)
        )

    def get_item_iri(self, item):
        return osfid_iri(item._id)

    def parse_metric_query_params(self):
        """Parses query parameters to a dict usable for fetching metrics.

        :param dict query_params:
        :return dict of the format {
            <usage_label>: <[daily|weekly|monthly|yearly|total]>,
        }
        """
        query = {}
        for key, value in self.request.query_params.items():
            _usage_label = self.METRICS_QUERY_MAP.get(key)
            if _usage_label:
                if value not in self.VALID_METRIC_PERIODS:
                    raise InvalidQueryStringError(f"Invalid period for metric: '{value}'", parameter='metrics')
                query[_usage_label] = value
        return query

    def add_metrics_to_object(self, obj):
        """Helper method used for detail views.
        """
        for _action_label, _period in self.parse_metric_query_params().items():
            _count = self._get_usage_count(self.get_item_iri(obj), _action_label, _period)
            setattr(obj, self.METRICS_ATTR_MAP[_action_label], _count)

    def _get_usage_count(self, item_iri, action_label, period):
        _search = (
            OsfCountedUsageEvent.search()
            .filter('term', item_iri=item_iri)
            .filter('term', action_labels=action_label.value)
        )
        _prior_count = 0
        if _timespan := self.TIMESPAN_MAP.get(period):
            _search = _search.filter('range', timestamp={'gte': _timespan})
        else:  # cumulative total
            _latest_usage_report = self._get_latest_usage_report(item_iri)
            if _latest_usage_report:
                _search = _search.filter(
                    'range', timestamp={
                        'gte': _latest_usage_report.report_yearmonth.month_end(),
                    },
                )
                if action_label == OsfCountedUsageEvent.ActionLabel.VIEW:
                    _prior_count = _latest_usage_report.cumulative_view_count
                elif action_label == OsfCountedUsageEvent.ActionLabel.DOWNLOAD:
                    _prior_count = _latest_usage_report.cumulative_download_count
                else:
                    raise ValueError(f'unsupported action label {action_label!r}')
        _response = _search[0:0].execute()
        return _prior_count + _response.doc_count

    def _get_latest_usage_report(self, item_iri):
        _search = (
            MonthlyPublicItemUsageReport.search()
            .filter('term', item_iri=item_iri)
            .sort('-cycle_coverage')
        )
        _response = _search[0].execute()
        return _response[0] if _response else None


class MetricsSerializerMixin:
    @property
    def available_metrics(self):
        raise NotImplementedError(
            'MetricSerializerMixin subclasses must define an available_metrics (set) class variable.',
        )

    # Override JSONAPISerializer
    def get_meta(self, obj):
        meta = super().get_meta(obj)
        for metric in self.available_metrics:
            if hasattr(obj, metric):
                meta = meta or {'metrics': {}}
                meta['metrics'][metric] = getattr(obj, metric)
        return meta
