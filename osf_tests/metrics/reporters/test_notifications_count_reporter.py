import datetime
from django.test import TestCase
from osf.metrics.reporters import NotificationCountReporter
from osf.metrics.utils import YearMonth
from osf.models import NotificationType
from ._testutils import list_monthly_reports
from osf_tests.factories import NotificationSubscriptionFactory, UserFactory


class TestNotificationsCountReporter(TestCase):
    def setUp(self):
        self.now = datetime.datetime.now()
        self.year_month = YearMonth(self.now.year, self.now.month)
        self.month_start = self.year_month.month_start()
        self.month_end = self.year_month.month_end()

    @staticmethod
    def createNotificationSubscription(created, user, notification_type):
        notification_subscription = NotificationSubscriptionFactory(user=user, notification_type=notification_type)
        notification_subscription.created = created
        notification_subscription.save()

    def test_no_data(self):
        reports = list_monthly_reports(NotificationCountReporter(self.year_month))
        assert len(reports) == 1
        report = reports[0]
        assert report.notification_subscriptions_count == 0
        assert report.notification_subscriptions_users_count == 0

    def test_all_data_outside_month(self):
        user = UserFactory()
        # Before the month
        self.createNotificationSubscription(
            user=user,
            created=self.month_start - datetime.timedelta(days=1),
            notification_type=NotificationType.Type.NODE_FILES_UPDATED.instance
        )
        # After the month
        self.createNotificationSubscription(
            user=user,
            created=self.month_end + datetime.timedelta(days=1),
            notification_type=NotificationType.Type.NODE_REQUEST_ACCESS_SUBMITTED.instance
        )
        reports = list_monthly_reports(NotificationCountReporter(self.year_month))
        assert len(reports) == 1
        report = reports[0]
        assert report.notification_subscriptions_count == 0
        assert report.notification_subscriptions_users_count == 0

    def test_single_subscription_in_month(self):
        user = UserFactory()
        self.createNotificationSubscription(
            user=user,
            created=self.month_start + datetime.timedelta(days=1),
            notification_type=NotificationType.Type.NODE_REQUEST_ACCESS_SUBMITTED.instance
        )
        reports = list_monthly_reports(NotificationCountReporter(self.year_month))
        assert len(reports) == 1
        report = reports[0]

        assert report.notification_subscriptions_count == 1
        assert report.notification_subscriptions_users_count == 1

    def test_multiple_subscriptions_same_user(self):
        user = UserFactory()
        self.createNotificationSubscription(
            user=user,
            created=self.month_start + datetime.timedelta(days=2),
            notification_type=NotificationType.Type.NODE_REQUEST_ACCESS_SUBMITTED.instance
        )
        self.createNotificationSubscription(
            user=user,
            created=self.month_start + datetime.timedelta(days=3),
            notification_type=NotificationType.Type.NODE_INSTITUTIONAL_ACCESS_REQUEST.instance
        )
        reports = list_monthly_reports(NotificationCountReporter(self.year_month))
        assert len(reports) == 1
        report = reports[0]
        assert report.notification_subscriptions_count == 2
        assert report.notification_subscriptions_users_count == 1

    def test_multiple_users_multiple_subscriptions(self):
        user1 = UserFactory()
        user2 = UserFactory()
        self.createNotificationSubscription(
            user=user1,
            created=self.month_start + datetime.timedelta(days=2),
            notification_type=NotificationType.Type.NODE_AFFILIATION_CHANGED.instance
        )
        self.createNotificationSubscription(
            user=user1,
            created=self.month_start + datetime.timedelta(days=3),
            notification_type=NotificationType.Type.NODE_FILE_UPDATED.instance
        )
        self.createNotificationSubscription(
            user=user2,
            created=self.month_start + datetime.timedelta(days=4),
            notification_type=NotificationType.Type.NODE_REQUEST_ACCESS_SUBMITTED.instance
        )
        reports = list_monthly_reports(NotificationCountReporter(self.year_month))
        assert len(reports) == 1
        report = reports[0]
        assert report.notification_subscriptions_count == 3
        assert report.notification_subscriptions_users_count == 2

    def test_subscriptions_spanning_months(self):
        user1 = UserFactory()
        user2 = UserFactory()
        # One in previous month, one in current, one in next
        self.createNotificationSubscription(
            user=user1,
            created=self.month_start - datetime.timedelta(days=1),
            notification_type=NotificationType.Type.NODE_REQUEST_ACCESS_SUBMITTED.instance
        )
        self.createNotificationSubscription(
            user=user1,
            created=self.month_start + datetime.timedelta(days=1),
            notification_type=NotificationType.Type.NODE_INSTITUTIONAL_ACCESS_REQUEST.instance
        )
        self.createNotificationSubscription(
            user=user2,
            created=self.month_end + datetime.timedelta(days=1),
            notification_type=NotificationType.Type.NODE_AFFILIATION_CHANGED.instance
        )
        reports = list_monthly_reports(NotificationCountReporter(self.year_month))
        assert len(reports) == 1
        report = reports[0]
        assert report.notification_subscriptions_count == 1
        assert report.notification_subscriptions_users_count == 1
