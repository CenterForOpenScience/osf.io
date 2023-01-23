from django.views.generic import TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin

from admin.base import settings
from admin.base.settings import KEEN_CREDENTIALS


class MetricsView(PermissionRequiredMixin, TemplateView):
    template_name = 'metrics/osf_metrics.html'
    permission_required = 'osf.view_metrics'
    raise_exception = True

    def get_context_data(self, **kwargs):

        kwargs.update(KEEN_CREDENTIALS.copy())
        return super(MetricsView, self).get_context_data(**kwargs)


class MetricsView2(PermissionRequiredMixin, TemplateView):
    template_name = 'metrics/osf_metrics-mw.html'
    permission_required = 'osf.view_metrics'
    raise_exception = True

    def get_context_data(self, **kwargs):
        kwargs.update(KEEN_CREDENTIALS.copy())
        api_report_url = '{}_/metrics/reports/'.format(settings.API_DOMAIN)
        kwargs.update({'metrics_url': api_report_url})
        return super(MetricsView2, self).get_context_data(**kwargs)
