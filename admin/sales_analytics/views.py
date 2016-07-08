from django.views.generic import TemplateView

from admin.base.settings import ENTRY_POINTS
from admin.base.settings import KEEN_CREDENTIALS
from admin.base.utils import OSFAdmin
from admin.sales_analytics.utils import get_user_count, get_multi_product_metrics, get_repeat_action_user_count
from datetime import timedelta


class DashboardView(OSFAdmin, TemplateView):
    template_name = 'sales_analytics/dashboard.html'

    def get_context_data(self, **kwargs):
        user_count = get_user_count(entry_points=ENTRY_POINTS)
        multi_product_metrics_yearly = get_multi_product_metrics()
        multi_product_metrics_monthly = get_multi_product_metrics(timedelta=timedelta(days=30))
        repeat_action_user_monthly = get_repeat_action_user_count()

        kwargs.update(KEEN_CREDENTIALS.copy())
        kwargs.update({'user_count': user_count,
                       'multi_product_metrics_yearly': multi_product_metrics_yearly,
                       'multi_product_metrics_monthly': multi_product_metrics_monthly,
                       'repeat_action_user_monthly': repeat_action_user_monthly,
                       })
        return super(DashboardView, self).get_context_data(**kwargs)
