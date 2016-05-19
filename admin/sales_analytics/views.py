from django.views.generic import TemplateView

from admin.base.settings import KEEN_CREDENTIALS
from admin.base.utils import OSFAdmin
from admin.sales_analytics.utils import get_user_count, get_multi_product_metrics, get_repeat_action_user_count, get_user_count_history
from datetime import datetime, timedelta


class DashboardView(OSFAdmin, TemplateView):
    template_name = "sales_analytics/dashboard.html"

    def get_context_data(self, **kwargs):
        user_count = get_user_count()
        user_count_yesterday = get_user_count(date=datetime.now().date() - timedelta(days=1))
        multi_product_metrics_yearly = get_multi_product_metrics(timedelta=timedelta(days=365))
        multi_product_metrics_monthly = get_multi_product_metrics(timedelta=timedelta(days=30))
        repeat_action_user_monthly = get_repeat_action_user_count()

        count_history_monthly = get_user_count_history()

        kwargs.update(KEEN_CREDENTIALS.copy())
        kwargs.update({'user_count': user_count,
                       'user_added': user_count['total'] - user_count_yesterday['total'],
                       'multi_product_metrics_yearly': multi_product_metrics_yearly,
                       'multi_product_metrics_monthly': multi_product_metrics_monthly,
                       'repeat_action_user_monthly': repeat_action_user_monthly,
                       'count_history_monthly': count_history_monthly,
                       })
        return super(DashboardView, self).get_context_data(**kwargs)
