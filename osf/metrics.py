import datetime as dt

from elasticsearch_metrics import metrics
from django.db import models
from django.utils import timezone
import pytz

class MetricMixin(object):

    @classmethod
    def _get_relevant_indices(cls, after):
        # NOTE: This will only work for yearly indices. This logic
        # will need to be updated if we change to monthly or daily indices
        year_range = range(after.year, timezone.now().year + 1)
        return [
            # get_index_name takes a datetime, so get Jan 1 for each relevant year
            cls.get_index_name(dt.datetime(year, 1, 1, tzinfo=pytz.utc))
            for year in year_range
        ]

    @classmethod
    def _get_id_to_count(cls, size, metric_field, count_field, after=None):
        """Performs the elasticsearch aggregation for get_top_by_count. Return a
        dict mapping ids to summed counts. If there's no data in the ES index, return None.
        """
        search = cls.search(after=after)
        if after:
            search = search.filter('range', timestamp={'gte': after})
        search.aggs.\
            bucket('by_id', 'terms', field=metric_field, size=size, order={'sum_count': 'desc'}).\
            metric('sum_count', 'sum', field=count_field)
        # Optimization: set size to 0 so that hits aren't returned (we only care about the aggregation)
        response = search.extra(size=0).execute()
        # No indexed data
        if not hasattr(response.aggregations, 'by_id'):
            return None
        buckets = response.aggregations.by_id.buckets
        # Map _id => count
        return {
            bucket.key: int(bucket.sum_count.value)
            for bucket in buckets
        }

    # Overrides Document.search to only search relevant
    # indices, determined from `after`
    @classmethod
    def search(cls, using=None, index=None, after=None, *args, **kwargs):
        if not index and after:
            indices = cls._get_relevant_indices(after)
            index = ','.join(indices)
        return super(MetricMixin, cls).search(using=using, index=index, *args, **kwargs)

    @classmethod
    def get_top_by_count(cls, qs, model_field, metric_field,
                         size, order_by=None,
                         count_field='count',
                         annotation='metric_count', after=None):
        """Return a queryset annotated with the metric counts for each item.

        Example: ::

            # Get the top 10 PreprintProviders by download count
            top_providers = PreprintDownload.get_top_by_count(
                qs=PreprintProvider.objects.all(),
                model_field='_id',
                metric_field='provider_id',
                annotation='download_count',
                size=10
            )

            for each in top_providers:
                print('{}: {}'.format(each._id, each.download_count))

        ``size`` determines the number of buckets returned by the aggregation.
        If ``size=None``, the size of the queryset is used.
        WARNING: Be careful when using size=None when using a large queryset.

        :param QuerySet qs: The initial queryset to annotate
        :param str model_field: Model field that corresponds to ``metric_field``.
        :param str metric_field: Metric field that corresponds to ``model_field``.
        :param int size: Size of the aggregation. Also determines the size of the final
            queryset.
        :param str order_by: Field to order queryset by. If `None`, orders by
            the metric, descending.
        :param datetime after: Minimum datetime to narrow the search (inclusive).
        :param str count_field: Name of the field where count values are stored.
        :param str annotation: Name of the annotation.
        """
        id_to_count = cls._get_id_to_count(
            size=size or qs.count(),
            metric_field=metric_field,
            count_field=count_field,
            after=after,
        )
        if id_to_count is None:
            return qs.annotate(**{annotation: models.Value(0, models.IntegerField())})
        # Annotate the queryset with the counts for each id
        # https://stackoverflow.com/a/48187723/1157536
        whens = [
            models.When(**{
                model_field: k,
                'then': v,
            }) for k, v in id_to_count.items()
        ]
        # By default order by annotation, desc
        order_by = order_by or '-{}'.format(annotation)
        return qs.annotate(**{
            annotation: models.Case(*whens, default=0, output_field=models.IntegerField())
        }).order_by(order_by)


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
    def get_count_for_preprint(cls, preprint, after=None):
        search = cls.search(after=after).filter('match', preprint_id=preprint._id)
        if after:
            search = search.filter('range', timestamp={'gte': after})
        search.aggs.metric('sum_count', 'sum', field='count')
        # Optimization: set size to 0 so that hits aren't returned (we only care about the aggregation)
        response = search.extra(size=0).execute()
        # No indexed data
        if not hasattr(response.aggregations, 'sum_count'):
            return 0
        return int(response.aggregations.sum_count.value)


class PreprintView(BasePreprintMetric):
    pass


class PreprintDownload(BasePreprintMetric):
    pass
