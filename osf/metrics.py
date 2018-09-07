from elasticsearch_metrics import metrics
from django.db import models

class MetricMixin(object):

    @classmethod
    def get_top_by_count(cls, qs, model_field, metric_field, size=None, order_by=None, annotation='metric_count'):
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
        :parm str order_by: Field to order queryset by. If `None`, orders by
            the metric, descending.
        :param str annotation: Name of the annotation.
        """
        search = cls.search()
        size = size or qs.count()
        search.aggs.bucket('by_id', 'terms', field=metric_field, size=size)
        response = search.execute()
        # No indexed data
        if not hasattr(response.aggregations, 'by_id'):
            return qs.annotate(**{annotation: models.Value(0, models.IntegerField())})
        buckets = response.aggregations.by_id.buckets
        # Map _id => count
        id_to_count = {
            bucket.key: bucket.doc_count
            for bucket in buckets
        }
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
    provider_id = metrics.Keyword(index=True, doc_values=True, required=True)
    user_id = metrics.Keyword(index=True, doc_values=True, required=True)
    preprint_id = metrics.Keyword(index=True, doc_values=True, required=True)
    # TODO: Make these required when we can get these fields in the
    # waterbutler auth callback
    version = metrics.Keyword(index=True, doc_values=True)
    path = metrics.Text(index=True)
    # TODO: locale

    class Index:
        settings = {
            'number_of_shards': 2,
        }

    class Meta:
        abstract = True

    @classmethod
    def get_count_for_preprint(cls, preprint):
        return cls.search().filter('match', preprint_id=preprint._id).count()


class PreprintView(BasePreprintMetric):
    pass


class PreprintDownload(BasePreprintMetric):
    pass
