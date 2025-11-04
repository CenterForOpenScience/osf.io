import pytest
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
        kwargs['subscribed_object'] = provider
    if provider is not None:
        kwargs['subscribed_object'] = subscription
    return NotificationSubscription.objects.create(**kwargs)


@pytest.mark.django_db
def test_send_user_email_task_success(fake):
    user = AuthUserFactory()
    notification_type = NotificationType.objects.get(name=NotificationType.Type.USER_DIGEST)
    notification = Notification.objects.create(
        subscription=add_notification_subscription(user, NotificationType.Type.USER_FILE_UPDATED, notification_type, 'daily'),
        sent=None,
        # event_context={'osf_logo': 'logo_url', 'source_addon': 'source_addon', 'action': 'action', 'file_name': 'file_name', 'osf_logo_list': []},
        event_context={
            'user_fullname': 'user_fullname',
            'action': 'action',
            'source_node': 'source_node',
            'source_node_title': 'source_node_title',
            'destination_node': 'destination_node',
            'destination_node_title': 'destination_node_title',
            'destination_node_parent_node_title': 'destination_node_parent_node_title',
            'source_path': 'source_path',
            'source_addon': 'source_addon',
            'destination_addon': 'destination_addon',
            'osf_support_email': 'osf_support_email',
            'logo': 'logo',
            'osf_logo_list': 'OSF_LOGO_LIST',
            'osf_logo': 'osf_logo',
        }
    )
    user.save()
    notification_ids = [notification.id]
    with capture_notifications() as notifications:
        send_user_email_task.apply(args=(user._id, notification_ids)).get()
    assert len(notifications['emits']) == 1
    assert notifications['emits'][0]['type'] == NotificationType.Type.USER_DIGEST
    email_task = EmailTask.objects.get(user_id=user.id)
    assert email_task.status == 'SUCCESS'
    notification.refresh_from_db()
    assert notification.sent

@pytest.mark.django_db
def test_send_user_email_task_user_not_found():
    non_existent_user_id = 'fakeuserid'
    notification_ids = []
    send_user_email_task.apply(args=(non_existent_user_id, notification_ids)).get()
    assert EmailTask.objects.all().exists()
    email_task = EmailTask.objects.all().get()
    assert email_task.status == 'NO_USER_FOUND'
    assert email_task.error_message == 'User not found or disabled'

@pytest.mark.django_db
def test_send_user_email_task_user_disabled(fake):
    user = AuthUserFactory()
    user.deactivate_account()
    user.save()
    notification_type = NotificationType.objects.get(name=NotificationType.Type.USER_DIGEST)
    notification = Notification.objects.create(
        subscription=add_notification_subscription(user, NotificationType.Type.USER_FILE_UPDATED, notification_type, 'daily'),
        sent=None,
        event_context={},
    )
    notification_ids = [notification.id]
    send_user_email_task.apply(args=(user._id, notification_ids)).get()
    email_task = EmailTask.objects.filter(user_id=user.id).first()
    assert email_task.status == 'USER_DISABLED'
    assert email_task.error_message == 'User not found or disabled'

@pytest.mark.django_db
def test_send_user_email_task_no_notifications(fake):
    user = AuthUserFactory()
    notification_ids = []
    send_user_email_task.apply(args=(user._id, notification_ids)).get()
    email_task = EmailTask.objects.filter(user_id=user.id).first()
    assert email_task.status == 'SUCCESS'

@pytest.mark.django_db
def test_send_moderator_email_task_registration_provider_admin(fake):
    user = AuthUserFactory(fullname='Admin User')
    reg_provider = RegistrationProviderFactory(_id='abc123')
    admin_group = reg_provider.get_group('admin')
    admin_group.user_set.add(user)
    notification_type = NotificationType.objects.get(name=NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS)
    notification = Notification.objects.create(
        subscription=add_notification_subscription(user, notification_type, 'daily', provider=reg_provider),
        event_context={
            'provider_id': reg_provider.id,
            'submitter_fullname': 'submitter_fullname',
            'requester_fullname': 'requester_fullname',
            'requester_contributor_names': 'requester_contributor_names',
            'localized_timestamp': '2024-01-01T00:00:00Z',
            'message': 'submitted title.',
            'reviews_submission_url': 'reviews_submission_url',
            'is_request_email': False,
            'is_initiator': False,
            'profile_image_url': 'profile_image_url'
        },
        sent=None,
    )
    notification_ids = [notification.id]
    send_moderator_email_task.apply(args=(user._id, reg_provider.id, notification_ids)).get()
    email_task = EmailTask.objects.filter(user_id=user.id).first()
    assert email_task.status == 'SUCCESS'
    notification.refresh_from_db()
    assert notification.sent

@pytest.mark.django_db
def test_send_moderator_email_task_no_notifications(fake):
    user = AuthUserFactory(fullname='Admin User')
    provider = RegistrationProviderFactory()
    notification_ids = []
    send_moderator_email_task.apply(args=(user._id, provider.id, notification_ids)).get()
    email_task = EmailTask.objects.filter(user_id=user.id).first()
    assert email_task.status == 'SUCCESS'

@pytest.mark.django_db
def test_send_moderator_email_task_user_not_found():
    provider = RegistrationProviderFactory()
    send_moderator_email_task.apply(args=('nouser', provider.id, [])).get()
    email_task = EmailTask.objects.filter()
    assert email_task.exists()
    assert email_task.first().status == 'NO_USER_FOUND'

@pytest.mark.django_db
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

# Reasoning:
# Test get_moderators_emails returns grouped emails by user and provider.
@pytest.mark.django_db
def test_get_moderators_emails(fake):
    user = AuthUserFactory()
    provider = RegistrationProviderFactory()
    notification_type = NotificationType.objects.get(name=NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS)
    Notification.objects.create(
        subscription=add_notification_subscription(user, notification_type, 'daily', provider=provider),
        event_context={'provider_id': provider.id},
        sent=None
    )
    res = list(get_moderators_emails('daily'))
    assert len(res) >= 1
    entry = [
        x for x in res if x['user_id'] == user._id and x['provider_id'] == str(provider.id)
    ]
    assert entry, 'Expected moderator digest group'

@pytest.mark.django_db
def test_send_users_digest_email_end_to_end(fake):
    user = AuthUserFactory()
    notification_type = NotificationType.objects.get(name=NotificationType.Type.USER_DIGEST)
    Notification.objects.create(
        subscription=add_notification_subscription(user, notification_type, 'daily'),
        sent=None,
        event_context={'notifications': ['1', '2']},
    )
    with capture_notifications() as notifications:
        send_users_digest_email()
    assert len(notifications['emits']) == 1
    assert notifications['emits'][0]['type'] == NotificationType.Type.USER_DIGEST
    email_task = EmailTask.objects.get(user_id=user.id)
    assert email_task.status == 'SUCCESS'

@pytest.mark.django_db
def test_send_moderators_digest_email_end_to_end(fake):
    user = AuthUserFactory()
    provider = RegistrationProviderFactory()
    notification_type = NotificationType.objects.get(name=NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS)
    Notification.objects.create(
        subscription=add_notification_subscription(user, notification_type, 'daily', provider=provider),
        sent=None,
        event_context={
            'provider_id': provider.id,
            'submitter_fullname': 'submitter_fullname',
            'requester_fullname': 'requester_fullname',
            'requester_contributor_names': 'requester_contributor_names',
            'localized_timestamp': '2024-01-01T00:00:00Z',
            'message': 'submitted title.',
            'reviews_submission_url': 'reviews_submission_url',
            'is_request_email': False,
            'is_initiator': False,
            'profile_image_url': 'profile_image_url'
        },
    )
    with capture_notifications() as notifications:
        send_moderators_digest_email.delay()
    assert len(notifications['emits']) == 1
    assert notifications['emits'][0]['type'] == NotificationType.Type.DIGEST_REVIEWS_MODERATORS
    email_task = EmailTask.objects.filter(user_id=user.id).first()
    assert email_task.status == 'SUCCESS'
