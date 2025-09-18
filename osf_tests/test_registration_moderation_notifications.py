import pytest
from unittest import mock

from django.utils import timezone

from notifications.tasks import send_users_digest_email
from osf.management.commands.populate_notification_types import populate_notification_types
from osf.migrations import update_provider_auth_groups
from osf.models import Brand, NotificationSubscription, NotificationType
from osf.models.action import RegistrationAction
from osf.utils.notifications import (
    notify_submit,
    notify_moderator_registration_requests_withdrawal,
    notify_reject_withdraw_request,
    notify_withdraw_registration
)
from osf.utils.workflows import RegistrationModerationTriggers, RegistrationModerationStates

from osf_tests.factories import (
    RegistrationFactory,
    AuthUserFactory,
    RetractionFactory
)
from tests.utils import capture_notifications

def get_moderator(provider):
    user = AuthUserFactory()
    provider.add_to_group(user, 'moderator')
    return user


def get_daily_moderator(provider):
    user = AuthUserFactory()
    provider.add_to_group(user, 'moderator')
    for subscription_type in provider.DEFAULT_SUBSCRIPTIONS:
        provider.notification_subscriptions.get(event_name=subscription_type)
    return user


# Set USE_EMAIL to true and mock out the default mailer for consistency with other mocked settings
@pytest.mark.django_db
class TestRegistrationMachineNotification:

    MOCK_NOW = timezone.now()

    @pytest.fixture(autouse=True)
    def setup(self):
        populate_notification_types()
        with mock.patch('osf.utils.machines.timezone.now', return_value=self.MOCK_NOW):
            yield

    @pytest.fixture()
    def contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def admin(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration(self, admin, contrib):
        registration = RegistrationFactory(creator=admin)
        registration.add_contributor(admin, 'admin')
        registration.add_contributor(contrib, 'write')
        update_provider_auth_groups()
        return registration

    @pytest.fixture()
    def registration_with_retraction(self, admin, contrib):
        sanction = RetractionFactory(user=admin)
        registration = sanction.target_registration
        registration.update_moderation_state()
        registration.add_contributor(admin, 'admin')
        registration.add_contributor(contrib, 'write')
        registration.save()
        return registration

    @pytest.fixture()
    def provider(self, registration):
        return registration.provider

    @pytest.fixture()
    def moderator(self, provider):
        user = AuthUserFactory()
        provider.add_to_group(user, 'moderator')
        return user

    @pytest.fixture()
    def daily_moderator(self, provider):
        user = AuthUserFactory()
        provider.add_to_group(user, 'moderator')
        return user

    @pytest.fixture()
    def accept_action(self, registration, admin):
        registration_action = RegistrationAction.objects.create(
            creator=admin,
            target=registration,
            trigger=RegistrationModerationTriggers.ACCEPT_SUBMISSION.db_name,
            from_state=RegistrationModerationStates.INITIAL.db_name,
            to_state=RegistrationModerationStates.ACCEPTED.db_name,
            comment='yo'
        )
        return registration_action

    @pytest.fixture()
    def withdraw_request_action(self, registration, admin):
        registration_action = RegistrationAction.objects.create(
            creator=admin,
            target=registration,
            trigger=RegistrationModerationTriggers.REQUEST_WITHDRAWAL.db_name,
            from_state=RegistrationModerationStates.ACCEPTED.db_name,
            to_state=RegistrationModerationStates.PENDING_WITHDRAW.db_name,
            comment='yo'
        )
        return registration_action

    @pytest.fixture()
    def withdraw_action(self, registration, admin):
        registration_action = RegistrationAction.objects.create(
            creator=admin,
            target=registration,
            trigger=RegistrationModerationTriggers.ACCEPT_WITHDRAWAL.db_name,
            from_state=RegistrationModerationStates.PENDING_WITHDRAW.db_name,
            to_state=RegistrationModerationStates.WITHDRAWN.db_name,
            comment='yo'
        )
        return registration_action

    def test_submit_notifications(self, registration, moderator, admin, contrib, provider):
        """
        [REQS-96] "As moderator of branded registry, I receive email notification upon admin author(s) submission approval"
        """
        with capture_notifications() as notification:
            notify_submit(registration, admin)

        assert len(notification['emits']) == 3
        assert notification['emits'][0]['type'] == NotificationType.Type.PROVIDER_REVIEWS_SUBMISSION_CONFIRMATION
        assert notification['emits'][0]['kwargs']['user'] == admin
        assert notification['emits'][1]['type'] == NotificationType.Type.PROVIDER_REVIEWS_SUBMISSION_CONFIRMATION
        assert notification['emits'][1]['kwargs']['user'] == contrib
        assert notification['emits'][2]['type'] == NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS

        assert NotificationSubscription.objects.count() == 5
        digest = NotificationSubscription.objects.last()
        assert digest.user == moderator

    def test_withdrawal_registration_accepted_notifications(
            self, registration_with_retraction, contrib, admin, withdraw_action
    ):
        """
        [REQS-109] Authors receive notification when withdrawal is accepted.
        Compare recipients by user objects via captured emits.
        """
        with capture_notifications() as notification:
            notify_withdraw_registration(registration_with_retraction, withdraw_action)

        recipients = {rec['kwargs']['user'] for rec in notification['emits'] if 'user' in rec['kwargs']}
        assert {admin, contrib}.issubset(recipients)

    def test_withdrawal_registration_rejected_notifications(
            self, registration, contrib, admin, withdraw_request_action
    ):
        """
        [REQS-109] Authors receive notification when withdrawal is rejected.
        Compare recipients by user objects via captured emits.
        """
        with capture_notifications() as notification:
            notify_reject_withdraw_request(registration, withdraw_request_action)

        recipients = {rec['kwargs']['user'] for rec in notification['emits'] if 'user' in rec['kwargs']}
        assert {admin, contrib}.issubset(recipients)

    def test_withdrawal_registration_force_notifications(
            self, registration_with_retraction, contrib, admin, withdraw_action
    ):
        """
        [REQS-109] Forced withdrawal route: compare recipients by user objects via captured emits.
        """
        with capture_notifications() as notification:
            notify_withdraw_registration(registration_with_retraction, withdraw_action)

        recipients = {rec['kwargs']['user'] for rec in notification['emits'] if 'user' in rec['kwargs']}
        assert {admin, contrib}.issubset(recipients)

    def test_moderator_digest_emails_render(self, registration, admin, moderator):
        with capture_notifications():
            notify_moderator_registration_requests_withdrawal(registration, admin)
            send_users_digest_email()

    def test_branded_provider_notification_renders(self, registration, admin, moderator):
        provider = registration.provider
        provider.brand = Brand.objects.create(hero_logo_image='not-a-url', primary_color='#FFA500')
        provider.name = 'Test Provider'
        provider.save()

        with capture_notifications():
            notify_submit(registration, admin)
