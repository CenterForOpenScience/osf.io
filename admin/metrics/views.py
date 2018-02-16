from django.views.generic import TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin

from admin.base.settings import KEEN_CREDENTIALS
from framework.analytics import get_basic_counters
from osf.models.files import File, TrashedFile


class MetricsView(PermissionRequiredMixin, TemplateView):
    template_name = 'metrics/osf_metrics.html'
    permission_required = 'osf.view_metrics'
    raise_exception = True

    def get_context_data(self, **kwargs):

        kwargs.update(KEEN_CREDENTIALS.copy())
        return super(MetricsView, self).get_context_data(**kwargs)

    def get_number_downloads_unique_and_total(self):
        number_downloads_unique = 0
        number_downloads_total = 0

        for file_node in File.objects.all():
            page = ':'.join(['download', file_node.node._id, file_node._id])
            unique, total = get_basic_counters(page)
            number_downloads_unique += unique or 0
            number_downloads_total += total or 0

        for file_node in TrashedFile.objects.all():
            page = ':'.join(['download', file_node.node._id, file_node._id])
            unique, total = get_basic_counters(page)
            number_downloads_unique += unique or 0
            number_downloads_total += total or 0

        return number_downloads_unique, number_downloads_total
