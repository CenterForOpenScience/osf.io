from django.views.generic import TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin

from admin.base import settings


class MetricsView(PermissionRequiredMixin, TemplateView):
    template_name = 'metrics/osf_metrics.html'
    permission_required = 'osf.view_metrics'
    raise_exception = True

    def get_context_data(self, **kwargs):
        api_report_url = f'{settings.API_DOMAIN}_/metrics/reports/'
        kwargs.update({'metrics_url': api_report_url})
        return super().get_context_data(**kwargs)
