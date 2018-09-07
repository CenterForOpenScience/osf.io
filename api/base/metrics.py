from api.base.exceptions import InvalidQueryStringError


class MetricMixin(object):
    @property
    def metric_map(self):
        raise NotImplementedError('MetricMixin sublcasses must define a metric_map class variable.')

    def get_annotated_queryset_with_metrics(self, queryset, metric_class, metric_name):
        """Return a queryset annotated with metrics. Use for list endpoints that expose metrics."""
        raise NotImplementedError('MetricMixin subclasses must define get_annotated_queryset_with_metrics().')

    def add_metric_to_object(self, obj, metric_class, metric_name):
        """Set an attribute for a metric on obj. Use for detail endpoints that expose metrics."""
        raise NotImplementedError('MetricMixin subclasses must define add_metric_to_object().')

    @property
    def metrics_requested(self):
        return bool(self.request.query_params.get('metrics', False))

    # TODO: DRY up this and get_metrics_queryset
    def add_metrics_to_object(self, obj):
        metric_param = self.request.query_params.get('metrics', None)
        if metric_param:
            metric_map = self.metric_map
            metrics = [each.lower().strip() for each in metric_param.split(',')]
            for metric in metrics:
                if metric not in metric_map:
                    raise InvalidQueryStringError('Invalid metric in query string: {}'.format(metric))
                metric_class = metric_map[metric]
                self.add_metric_to_object(obj, metric_class, metric)
        return obj

    def get_metrics_queryset(self, queryset):
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

    # Override get_default_queryset for convenience
    def get_default_queryset(self):
        queryset = super(MetricMixin, self).get_default_queryset()
        return self.get_metrics_queryset(queryset)

class MetricsSerializerMixin(object):
    @property
    def available_metrics(self):
        raise NotImplementedError(
            'MetricSerializerMixin subclasses must define an available_metrics (set) class variable.'
        )

    def get_meta(self, obj):
        meta = super(MetricsSerializerMixin, self).get_meta(obj)
        for metric in self.available_metrics:
            if hasattr(obj, metric):
                meta = meta or {'metrics': {}}
                meta['metrics'][metric] = getattr(obj, metric)
        return meta
