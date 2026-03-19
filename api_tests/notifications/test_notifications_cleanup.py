import pytest
from osf.models import Notification, NotificationType, EmailTask, NotificationSubscription
from notifications.tasks import (
    notifications_cleanup_task
)
from osf_tests.factories import AuthUserFactory
from website.settings import NOTIFICATIONS_CLEANUP_AGE
from django.utils import timezone
from datetime import timedelta

def create_notification(subscription, sent_date=None):
    return Notification.objects.create(
        subscription=subscription,
        event_context={},
        sent=sent_date
    )

def create_email_task(user, created_date):
    et = EmailTask.objects.create(
        task_id=f'test-{created_date.timestamp()}',
        user=user,
        status='SUCCESS',
    )
    et.created_at = created_date
    et.save()
    return et

@pytest.mark.django_db
class TestNotificationCleanUpTask:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def notification_type(self):
        return NotificationType.objects.get_or_create(
            name='Test Notification',
            subject='Hello',
            template='Sample Template',
        )[0]

    @pytest.fixture()
    def subscription(self, user, notification_type):
        return NotificationSubscription.objects.get_or_create(
            user=user,
            notification_type=notification_type,
            message_frequency='daily',
        )[0]

    def test_dry_run_does_not_delete_records(self, user, subscription):
        now = timezone.now()

        old_notification = create_notification(
            subscription,
            sent_date=now - NOTIFICATIONS_CLEANUP_AGE - timedelta(days=1),
        )
        old_email_task = create_email_task(
            user,
            created_date=now - NOTIFICATIONS_CLEANUP_AGE - timedelta(days=1),
        )

        notifications_cleanup_task(dry_run=True)

        assert Notification.objects.filter(id=old_notification.id).exists()
        assert EmailTask.objects.filter(id=old_email_task.id).exists()

    def test_deletes_old_notifications_and_email_tasks(self, user, subscription):
        now = timezone.now()

        old_notification = create_notification(
            subscription,
            sent_date=now - NOTIFICATIONS_CLEANUP_AGE - timedelta(days=1),
        )
        new_notification = create_notification(
            subscription,
            sent_date=now - timedelta(days=10),
        )

        old_email_task = create_email_task(
            user,
            created_date=now - NOTIFICATIONS_CLEANUP_AGE - timedelta(days=1),
        )
        new_email_task = create_email_task(
            user,
            created_date=now - timedelta(days=10),
        )

        notifications_cleanup_task()

        assert not Notification.objects.filter(id=old_notification.id).exists()
        assert Notification.objects.filter(id=new_notification.id).exists()

        assert not EmailTask.objects.filter(id=old_email_task.id).exists()
        assert EmailTask.objects.filter(id=new_email_task.id).exists()

    def test_records_at_cutoff_are_not_deleted(self, user, subscription):
        now = timezone.now()
        cutoff = now - NOTIFICATIONS_CLEANUP_AGE + timedelta(hours=1)

        notification = create_notification(
            subscription,
            sent_date=cutoff,
        )
        email_task = create_email_task(
            user,
            created_date=cutoff,
        )

        notifications_cleanup_task()

        assert Notification.objects.filter(id=notification.id).exists()
        assert EmailTask.objects.filter(id=email_task.id).exists()

    def test_cleanup_when_only_notifications_exist(self, user, subscription):
        now = timezone.now()

        notification = create_notification(
            subscription,
            sent_date=now - NOTIFICATIONS_CLEANUP_AGE - timedelta(days=1),
        )

        notifications_cleanup_task()

        assert not Notification.objects.filter(id=notification.id).exists()

    def test_cleanup_when_only_email_tasks_exist(self, user, subscription):
        now = timezone.now()

        email_task = create_email_task(
            user,
            created_date=now - NOTIFICATIONS_CLEANUP_AGE - timedelta(days=1),
        )

        notifications_cleanup_task()

        assert not EmailTask.objects.filter(id=email_task.id).exists()

    def test_task_is_idempotent(self, user, subscription):
        now = timezone.now()

        create_notification(
            subscription,
            sent_date=now - NOTIFICATIONS_CLEANUP_AGE - timedelta(days=1),
        )
        create_email_task(
            user,
            created_date=now - NOTIFICATIONS_CLEANUP_AGE - timedelta(days=1),
        )

        notifications_cleanup_task()
        notifications_cleanup_task()

        assert Notification.objects.count() == 0
        assert EmailTask.objects.count() == 0

    def test_recent_records_are_not_deleted(self, user, subscription):
        now = timezone.now()

        create_notification(
            subscription,
            sent_date=now - NOTIFICATIONS_CLEANUP_AGE - timedelta(days=1),
        )
        create_email_task(
            user,
            created_date=now - NOTIFICATIONS_CLEANUP_AGE - timedelta(days=1),
        )
        create_notification(
            subscription,
            sent_date=now,
        )
        create_email_task(
            user,
            created_date=now,
        )

        notifications_cleanup_task()

        assert Notification.objects.count() == 1
        assert EmailTask.objects.count() == 1

    def test_not_sent_notifications_are_not_deleted(self, user, subscription):
        create_notification(subscription)
        create_notification(subscription)
        create_notification(subscription)

        notifications_cleanup_task()

        assert Notification.objects.count() == 3
