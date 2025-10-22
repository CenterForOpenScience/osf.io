import pytest
from osf_tests.factories import (
    AuthUserFactory,
    NotificationTypeFactory
)
from osf.models import Notification, NotificationType, NotificationSubscription
from tests.utils import capture_notifications
from django.db import reset_queries, connection


@pytest.mark.django_db
class TestNotificationTypeDBTransaction:

    @pytest.fixture()
    def user_one(self):
        return AuthUserFactory()

    @pytest.fixture()
    def test_notification_type(self):
        return NotificationTypeFactory(
            name='test_notification_type',
            template='Test template for ${notifications}',
            subject='Test notification subject',
        )

    def test_notification_type_cache(self):
        NotificationType.Type.NODE_FILE_UPDATED.instance
        reset_queries()
        NotificationType.Type.NODE_FILE_UPDATED.instance
        assert len(connection.queries) == 0

    def test_emit_without_saving(self, user_one, test_notification_type):
        with capture_notifications():
            test_notification_type.emit(
                user=user_one,
                event_context={'notifications': 'test template for Test notification'},
                save=False
            )
        assert len(connection.queries) == 0
        assert not NotificationSubscription.objects.filter(
            user=user_one,
            notification_type=test_notification_type
        ).exists()
        assert not Notification.objects.filter(
            subscription__notification_type=test_notification_type
        ).exists()
