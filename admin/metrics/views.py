from django.views.generic import TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin

from admin.base.settings import KEEN_CREDENTIALS


class MetricsView(PermissionRequiredMixin, TemplateView):
    template_name = 'metrics/osf_metrics.html'
    permission_required = 'common_auth.view_metrics'
    raise_exception = True

    def get_context_data(self, **kwargs):

        kwargs.update(KEEN_CREDENTIALS.copy())
        return super(MetricsView, self).get_context_data(**kwargs)
