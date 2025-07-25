from osf.metrics.reports import (
    MonthlyReport,
    NotificationSummaryReport,
)
from osf.models.notification_subscription import NotificationSubscription

class NotificationCountReporter(MonthlyReport):
    report_name = 'Notification Metrics'

    def report(self):
        target_month = self.yearmonth.month_start()
        next_month = self.yearmonth.month_end()

        report = NotificationSummaryReport(
            report_yearmonth=str(self.yearmonth),
            notification_subscriptions_count=NotificationSubscription.objects.filter(
                created__gt=target_month, created__lt=next_month
            ).distinct().count(),
            notification_subscriptions_users_count=NotificationSubscription.objects.filter(
                created__gt=target_month, created__lt=next_month
            ).values('user').distinct().count(),
        )
        return [report]
