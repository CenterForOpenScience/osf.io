import pytest
from osf_tests.factories import (
    AuthUserFactory,
    NotificationTypeFactory
)
from osf.models import Notification, NotificationType, NotificationSubscription
from tests.utils import get_mailhog_messages, delete_mailhog_messages
from django.db import reset_queries, connection
from waffle.testutils import override_switch
from osf import features


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
        reset_queries()
        with override_switch(features.ENABLE_MAILHOG, active=True):
            delete_mailhog_messages()
            test_notification_type.emit(
                user=user_one,
                event_context={'notifications': 'test template for Test notification'},
                save=False
            )
            assert len(connection.queries) == 0
            messages = get_mailhog_messages()
            assert messages['total'] == 1
            assert messages['items'][0]['Content']['Headers']['To'][0] == user_one.username
            assert messages['items'][0]['Content']['Body'] == 'Test template for test template for Test notification'
            delete_mailhog_messages()
        assert not NotificationSubscription.objects.filter(
            user=user_one,
            notification_type=test_notification_type
        ).exists()
        assert not Notification.objects.filter(
            subscription__notification_type=test_notification_type
        ).exists()
