from django.views.generic import TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin

from admin.base.settings import KEEN_CREDENTIALS


from admin.base.utils import OSFAdmin


class MetricsView(OSFAdmin, TemplateView, PermissionRequiredMixin):
    template_name = 'metrics/osf_metrics.html'
    permission_required = 'admin.view_metrics'

    def get_context_data(self, **kwargs):

        kwargs.update(KEEN_CREDENTIALS.copy())
        return super(MetricsView, self).get_context_data(**kwargs)
