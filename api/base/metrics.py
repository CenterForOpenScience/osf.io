from api.base.exceptions import InvalidQueryStringError


class MetricMixin(object):
    @property
    def metric_map(self):
        raise NotImplementedError('MetricMixin sublcasses must define a metric_map class variable.')

    def get_default_queryset(self):
        queryset = super(MetricMixin, self).get_default_queryset()
        metric_param = self.request.query_params.get('metrics', None)
        if metric_param:
            metric_map = self.metric_map
            metrics = [each.lower().strip() for each in metric_param.split(',')]
            for metric in metrics:
                if metric not in metric_map:
                    raise InvalidQueryStringError('Invalid metric in query string: {}'.format(metric))
                metric_class = metric_map[metric]
                queryset = self.get_annotated_queryset_with_metrics(queryset, metric_class, metric)
        return queryset

    def get_annotated_queryset_with_metrics(self, queryset, metric_class, metric_name):
        """Return a queryset annotated with metrics."""
        raise NotImplementedError('MetricMixin subclasses must define get_annotated_queryset_with_metrics().')
