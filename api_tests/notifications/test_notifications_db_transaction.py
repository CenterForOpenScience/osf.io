import pytest
from osf_tests.factories import (
    AuthUserFactory,
    NotificationTypeFactory
)
from datetime import datetime
from osf.models import Notification, NotificationTypeEnum, NotificationSubscription
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
        NotificationTypeEnum.NODE_FILE_UPDATED.instance
        reset_queries()
        NotificationTypeEnum.NODE_FILE_UPDATED.instance
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

    def test_emit_frequency_none(self, user_one, test_notification_type):
        test_notification_type.emit(
            user=user_one,
            event_context={'notifications': 'test template for Test notification'},
            message_frequency='none'
        )
        assert Notification.objects.filter(
            subscription__notification_type=test_notification_type,
            sent=datetime(1000, 1, 1)
        ).exists()
