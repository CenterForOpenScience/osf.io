import pytest
from django.contrib.contenttypes.models import ContentType

from osf.models import Notification, NotificationType, EmailTask
from notifications.tasks import (
    send_user_email_task,
    send_moderator_email_task,
    send_users_digest_email,
    send_moderators_digest_email,
    get_users_emails,
    get_moderators_emails
)
from osf_tests.factories import AuthUserFactory, RegistrationProviderFactory
from tests.utils import capture_notifications


def add_notification_subscription(user, notification_type, frequency, provider=None, subscription=None):
    """
    Create a NotificationSubscription for a user.
    If the notification type corresponds to a provider, set provider as the subscribed_object.
    """
    from osf.models import NotificationSubscription
    kwargs = {
        'user': user,
        'notification_type': NotificationType.objects.get(name=notification_type),
        'message_frequency': frequency,
    }
    if provider is not None:
        kwargs['object_id'] = provider.id
        kwargs['content_type'] = ContentType.objects.get_for_model(provider)
    if subscription is not None:
        kwargs['object_id'] = subscription.id
        kwargs['content_type'] = ContentType.objects.get_for_model(subscription)
    return NotificationSubscription.objects.create(**kwargs)


@pytest.mark.django_db
class TestNotificationDigestTasks:

    def test_send_user_email_task_success(fake):
        user = AuthUserFactory()
        notification_type = NotificationType.objects.get(name=NotificationType.Type.USER_FILE_UPDATED)
        subscription_type = add_notification_subscription(
            user,
            notification_type,
            'daily',
            subscription=add_notification_subscription(
                user,
                NotificationType.objects.get(name=NotificationType.Type.FILE_UPDATED),
                'daily'
            )
        )

        notification = Notification.objects.create(
            subscription=subscription_type,
            event_context={
                'source_path': '/',
                'source_node_title': 'test title',
                'source_addon': 'test addon',
                'destination_addon': 'what?',
                'logo': 'test logo',
                'action': 'test action',
                'osf_logo': 'test logo',
                'osf_logo_list': 'osf_logo_list',
                'destination_node_parent_node_title': 'test parent node title',
                'destination_node_title': 'test node title',
            },
        )
        user.save()
        notification_ids = [notification.id]
        with capture_notifications() as notifications:
            send_user_email_task.apply(args=(user._id, notification_ids)).get()
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.USER_DIGEST
        assert notifications['emits'][0]['kwargs']['user'] == user
        email_task = EmailTask.objects.get(user_id=user.id)
        assert email_task.status == 'SUCCESS'
        notification.refresh_from_db()
        assert notification.sent

    def test_send_user_email_task_user_not_found(self):
        non_existent_user_id = 'fakeuserid'
        notification_ids = []
        send_user_email_task.apply(args=(non_existent_user_id, notification_ids)).get()
        assert EmailTask.objects.all().exists()
        email_task = EmailTask.objects.all().get()
        assert email_task.status == 'NO_USER_FOUND'
        assert email_task.error_message == 'User not found or disabled'

    def test_send_user_email_task_user_disabled(self):
        user = AuthUserFactory()
        user.deactivate_account()
        user.save()
        notification_type = NotificationType.objects.get(name=NotificationType.Type.USER_DIGEST)
        notification = Notification.objects.create(
            subscription=add_notification_subscription(user, NotificationType.Type.USER_FILE_UPDATED, notification_type),
            sent=None,
            event_context={},
        )
        notification_ids = [notification.id]
        send_user_email_task.apply(args=(user._id, notification_ids)).get()
        email_task = EmailTask.objects.filter(user_id=user.id).first()
        assert email_task.status == 'USER_DISABLED'
        assert email_task.error_message == 'User not found or disabled'

    def test_send_user_email_task_no_notifications(self):
        user = AuthUserFactory()
        notification_ids = []
        send_user_email_task.apply(args=(user._id, notification_ids)).get()
        email_task = EmailTask.objects.filter(user_id=user.id).first()
        assert email_task.status == 'SUCCESS'

    def test_send_moderator_email_task_registration_provider_admin(self):
        user = AuthUserFactory(fullname='Admin User')
        reg_provider = RegistrationProviderFactory(_id='abc123')
        admin_group = reg_provider.get_group('admin')
        admin_group.user_set.add(user)
        notification_type = NotificationType.objects.get(name=NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS)
        notification = Notification.objects.create(
            subscription=add_notification_subscription(
                user,
                notification_type,
                'daily',
                provider=reg_provider
            ),
            event_context={
                'profile_image_url': 'http://example.com/profile.png',
                'is_request_email': False,
                'requester_contributor_names': ['<NAME>'],
                'reviews_submission_url': 'http://example.com/reviews_submission.png',
                'message': 'test message',
                'requester_fullname': '<NAME>',
                'localized_timestamp': 'test timestamp',
            },
            sent=None,
        )
        notification_ids = [notification.id]
        with capture_notifications() as notifications:
            send_moderator_email_task.apply(args=(user._id, notification_ids)).get()
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.DIGEST_REVIEWS_MODERATORS
        assert notifications['emits'][0]['kwargs']['user'] == user

        email_task = EmailTask.objects.filter(user_id=user.id).first()
        assert email_task.status == 'SUCCESS'
        notification.refresh_from_db()
        assert notification.sent

    def test_send_moderator_email_task_no_notifications(self):
        user = AuthUserFactory(fullname='Admin User')
        provider = RegistrationProviderFactory()
        notification_ids = []
        notification_type = NotificationType.objects.get(name=NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS)
        add_notification_subscription(
            user,
            notification_type,
            'daily',
            provider=provider
        )

        send_moderator_email_task.apply(args=(user._id, notification_ids)).get()
        email_task = EmailTask.objects.filter(user_id=user.id).first()
        assert email_task.status == 'SUCCESS'

    def test_send_moderator_email_task_user_not_found(self):
        send_moderator_email_task.apply(args=('nouser', [])).get()
        email_task = EmailTask.objects.filter()
        assert email_task.exists()
        assert email_task.first().status == 'NO_USER_FOUND'

    def test_get_users_emails(fake):
        user = AuthUserFactory()
        notification_type = NotificationType.objects.get(name=NotificationType.Type.USER_DIGEST)
        notification1 = Notification.objects.create(
            subscription=add_notification_subscription(user, notification_type, 'daily'),
            sent=None,
            event_context={},
        )
        res = list(get_users_emails('daily'))
        assert len(res) == 1
        user_info = res[0]
        assert user_info['user_id'] == user._id
        assert any(msg['notification_id'] == notification1.id for msg in user_info['info'])

    def test_get_moderators_emails(self):
        user = AuthUserFactory()
        provider = RegistrationProviderFactory()
        notification_type = NotificationType.objects.get(name=NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS)
        subscription = add_notification_subscription(user, notification_type, 'daily', provider=provider)
        Notification.objects.create(
            subscription=subscription,
            event_context={},
            sent=None
        )
        res = list(get_moderators_emails('daily'))
        assert len(res) >= 1
        entry = [
            x for x in res if x['user_id'] == user._id and subscription.subscribed_object.id == provider.id
        ]
        assert entry, 'Expected moderator digest group'

    def test_send_users_digest_email_end_to_end(self):
        user = AuthUserFactory()
        notification_type = NotificationType.objects.get(name=NotificationType.Type.USER_FILE_UPDATED)
        subscription_type = add_notification_subscription(
            user,
            notification_type,
            'daily',
            subscription=add_notification_subscription(
                user,
                NotificationType.objects.get(name=NotificationType.Type.FILE_UPDATED),
                'daily'
            )
        )

        Notification.objects.create(
            subscription=subscription_type,
            event_context={
                'source_path': '/',
                'requester_fullname': '<NAME>',
                'source_node_title': 'test title',
                'source_addon': 'test addon',
                'destination_addon': 'what?',
                'logo': 'test logo',
                'requester_contributor_names': ['<NAME>'],
                'action': 'test action',
                'osf_logo': 'test logo',
                'osf_logo_list': 'osf_logo_list',
                'profile_image_url': 'http://example.com/profile.png',
                'destination_node_parent_node_title': 'test parent node title',
                'destination_node_title': 'test node title',
                'nessage': 'test message',
                'localized_timestamp': 'test timestamp',
            },
        )
        user.save()
        with capture_notifications() as notifications:
            send_users_digest_email.delay()
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.USER_DIGEST
        email_task = EmailTask.objects.get(user_id=user.id)
        assert email_task.status == 'SUCCESS'

    def test_send_moderators_digest_email_end_to_end(self):
        user = AuthUserFactory()
        provider = RegistrationProviderFactory()
        notification_type = NotificationType.objects.get(name=NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS)
        Notification.objects.create(
            subscription=add_notification_subscription(user, notification_type, 'daily', provider=provider),
            sent=None,
            event_context={
                'reviews_submission_url': 'http://example.com/reviews_submission.png',
                'requester_contributor_names': ['<NAME>'],
                'is_request_email': False,
                'localized_timestamp': 'test timestamp',
                'requester_fullname': '<NAME>',
                'message': 'test message',
                'profile_image_url': 'http://example.com/profile.png',
            },
        )
        with capture_notifications() as notifications:
            send_moderators_digest_email.delay()
        assert len(notifications['emits']) == 1
        email_task = EmailTask.objects.filter(user_id=user.id).first()
        assert email_task.status == 'SUCCESS'
