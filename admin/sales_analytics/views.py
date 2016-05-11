from django.views.generic import TemplateView

from admin.base.settings import KEEN_CREDENTIALS
from admin.base.utils import OSFAdmin
from admin.sales_analytics.utils import user_count, multi_product_metrics_yearly, multi_product_metrics_monthly, repeat_action_user_monthly


class DashboardView(OSFAdmin, TemplateView):
    template_name = "sales_analytics/dashboard.html"

    def get_context_data(self, **kwargs):
        kwargs.update(KEEN_CREDENTIALS.copy())
        kwargs.update({'user_count': user_count,
                       'multi_product_metrics_yearly': multi_product_metrics_yearly,
                       'multi_product_metrics_monthly': multi_product_metrics_monthly,
                       'repeat_action_user_monthly': repeat_action_user_monthly,
                       })
        return super(DashboardView, self).get_context_data(**kwargs)

