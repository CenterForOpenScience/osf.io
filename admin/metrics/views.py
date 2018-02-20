from django.views.generic import TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin

from admin.base.settings import KEEN_CREDENTIALS
from osf.models.analytics import FileDownloadCounts


class MetricsView(PermissionRequiredMixin, TemplateView):
    template_name = 'metrics/osf_metrics.html'
    permission_required = 'osf.view_metrics'
    raise_exception = True

    def get_context_data(self, **kwargs):

        kwargs.update(KEEN_CREDENTIALS.copy())
        file_download_downs = {
            'number_downloads_total': FileDownloadCounts.number_downloads_total,
            'number_downloads_unique': FileDownloadCounts.number_downloads_unique
        }
        kwargs.update(file_download_downs)
        return super(MetricsView, self).get_context_data(**kwargs)
