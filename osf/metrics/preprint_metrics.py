from elasticsearch.exceptions import NotFoundError
from elasticsearch_metrics import metrics

from .metric_mixin import MetricMixin


class BasePreprintMetric(MetricMixin, metrics.Metric):
    count = metrics.Integer(doc_values=True, index=True, required=True)
    provider_id = metrics.Keyword(index=True, doc_values=True, required=True)
    user_id = metrics.Keyword(index=True, doc_values=True, required=False)
    preprint_id = metrics.Keyword(index=True, doc_values=True, required=True)
    version = metrics.Keyword(index=True, doc_values=True)
    path = metrics.Text(index=True)

    # TODO: locale

    class Index:
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 1,
            'refresh_interval': '1s',
        }

    class Meta:
        abstract = True
        source = metrics.MetaField(enabled=True)

    @classmethod
    def record_for_preprint(cls, preprint, user=None, **kwargs):
        count = kwargs.pop('count', 1)
        return cls.record(
            count=count,
            preprint_id=preprint._id,
            user_id=getattr(user, '_id', None),
            provider_id=preprint.provider._id,
            **kwargs
        )

    @classmethod
    def get_count_for_preprint(cls, preprint, after=None, before=None, index=None) -> int:
        search = cls.search(index=index).filter('term', preprint_id=preprint._id)
        timestamp = {}
        if after:
            timestamp['gte'] = after
        if before:
            timestamp['lt'] = before
        if timestamp:
            search = search.filter('range', timestamp=timestamp)
        search.aggs.metric('sum_count', 'sum', field='count')
        # Optimization: set size to 0 so that hits aren't returned (we only care about the aggregation)
        search = search.extra(size=0)
        try:
            response = search.execute()
        except NotFoundError:
            # _get_relevant_indices returned 1 or more indices
            # that doesn't exist. Fall back to unoptimized query
            search = search.index().index(cls._default_index())
            response = search.execute()
        # No indexed data
        if not hasattr(response.aggregations, 'sum_count'):
            return 0
        return int(response.aggregations.sum_count.value)


class PreprintView(BasePreprintMetric):
    pass


class PreprintDownload(BasePreprintMetric):
    pass
