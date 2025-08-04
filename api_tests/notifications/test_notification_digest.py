import pytest
from unittest.mock import patch

from datetime import datetime
from website.notifications.tasks import (
    send_users_email,
    get_users_emails,
    get_moderators_emails,
)
from osf_tests.factories import (
    AuthUserFactory,
    NotificationSubscriptionFactory,
    NotificationTypeFactory
)
from osf.models import Notification, NotificationType
from tests.utils import capture_notifications


@pytest.mark.django_db
class TestNotificationDigest:

    @pytest.fixture()
    def user_one(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def test_notification_type(self):
        return NotificationTypeFactory(
            name='test_notification_type',
            template='test template for {notifications}'
        )

    @pytest.fixture()
    def notifications_user_one(self, user_one):
        data = {'user': None, 'moderator': None}
        notification_subscription = NotificationSubscriptionFactory(
            user=user_one,
            notification_type=NotificationType.objects.get(name=NotificationType.Type.NODE_FILE_UPDATED),
            message_frequency='monthly',
        )
        notification_subscription.emit(event_context={'notifications': 'Test notification'})
        data['user'] = Notification.objects.get(subscription=notification_subscription).id

        notification_subscription = NotificationSubscriptionFactory(
            user=user_one,
            notification_type=NotificationType.objects.get(name=NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS),
            message_frequency='monthly',
        )
        notification_subscription.emit(event_context={'notifications': 'Test notification', 'provider_id': 1})
        data['moderator'] = Notification.objects.get(subscription=notification_subscription).id
        return data

    @pytest.fixture()
    def notifications_user_two(self, user_two, test_notification_type):
        data = {'user': None, 'moderator': None}
        notification_subscription = NotificationSubscriptionFactory(
            user=user_two,
            notification_type=NotificationType.objects.get(name='test_notification_type'),
            message_frequency='daily',
        )
        notification_subscription.emit(event_context={'notifications': 'Test notification'})
        data['user'] = Notification.objects.get(subscription=notification_subscription).id
        return data

    @patch('website.notifications.tasks._send_reviews_moderator_emails')
    @patch('website.notifications.tasks._send_global_and_node_emails')
    @patch('website.notifications.tasks.datetime')
    def test_send_users_email_daily(self, mock_datetime, mock__send_global_and_node_emails, mock__reviews_moderator_email):
        mock_datetime.today.return_value = datetime(2025, 8, 2)  # Saturday
        send_users_email()
        mock__send_global_and_node_emails.assert_called_once_with('daily')
        mock__reviews_moderator_email.assert_called_once_with('daily')

    @patch('website.notifications.tasks._send_reviews_moderator_emails')
    @patch('website.notifications.tasks._send_global_and_node_emails')
    @patch('website.notifications.tasks.datetime')
    def test_send_users_email_weekly(self, mock_datetime, mock__send_global_and_node_emails, mock__reviews_moderator_email):
        mock_datetime.today.return_value = datetime(2025, 8, 4)  # Monday
        send_users_email()
        assert mock__send_global_and_node_emails.call_count == 2
        assert mock__reviews_moderator_email.call_count == 2
        mock__send_global_and_node_emails.assert_any_call('daily')
        mock__send_global_and_node_emails.assert_any_call('weekly')

    @patch('website.notifications.tasks._send_reviews_moderator_emails')
    @patch('website.notifications.tasks._send_global_and_node_emails')
    @patch('website.notifications.tasks.datetime')
    def test_send_users_email_monthly(self, mock_datetime, mock__send_global_and_node_emails, mock__reviews_moderator_email):
        mock_datetime.today.return_value = datetime(2025, 6, 30)  # Last day of month and a Monday
        send_users_email()
        assert mock__send_global_and_node_emails.call_count == 3
        mock__send_global_and_node_emails.assert_any_call('daily')
        mock__send_global_and_node_emails.assert_any_call('weekly')
        mock__send_global_and_node_emails.assert_any_call('monthly')

    def test_get_emails(self, user_one, notifications_user_one):
        users_emails = get_users_emails('monthly')
        assert [el for el in users_emails] == [{'user_id': user_one._id, 'info': [{'notification_id': notifications_user_one['user']}]}]
        moderators_emails = get_moderators_emails('monthly')
        assert [el for el in moderators_emails] == [{'user_id': user_one._id, 'provider_id': '1', 'info': [{'notification_id': notifications_user_one['moderator']}]}]

    @patch('osf.models.Notification.send')
    def test_send_users_email_sends_notifications(self, mock_send, user_two, notifications_user_two):
        with capture_notifications() as notifications:
            send_users_email()

        assert mock_send.called
        assert Notification.objects.get(id=notifications_user_two['user']).sent
        assert notifications[0]['type'] == 'user_digest'
        assert notifications[0]['kwargs']['user'] == user_two
        assert notifications[0]['kwargs']['is_digest']
        assert notifications[0]['kwargs']['event_context'] == {
            'notifications': 'test template for Test notification',
            'user_fullname': user_two.fullname,
            'can_change_preferences': False
        }
