import pytest
import mock
from mock import call

from django.utils import timezone
from osf.management.commands.add_notification_subscription import add_reviews_notification_setting
from osf.management.commands.populate_registration_provider_notification_subscriptions import populate_registration_provider_notification_subscriptions

from osf.migrations import update_provider_auth_groups
from osf.models import Brand, NotificationDigest
from osf.models.action import RegistrationAction
from osf.utils import machines
from osf.utils.notifications import (
    notify_submit,
    notify_accept_reject,
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

from website import mails, settings
from website.notifications import emails, tasks
from website.reviews import listeners


# Set USE_EMAIL to true and mock out the default mailer for consistency with other mocked settings
@mock.patch('website.mails.settings.USE_EMAIL', True)
@mock.patch('website.mails.tasks.send_email', mock.MagicMock())
@pytest.mark.django_db
class TestRegistrationMachineNotification:

    MOCK_NOW = timezone.now()

    @pytest.yield_fixture(autouse=True)
    def setup(self):
        populate_registration_provider_notification_subscriptions()
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
        for subscription_type in provider.DEFAULT_SUBSCRIPTIONS:
            subscription = provider.notification_subscriptions.get(event_name=subscription_type)
            subscription.add_user_to_subscription(user, 'email_digest')
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
        :param mock_email:
        :param draft_registration:
        :return:
        """
        # Set up mock_send_mail as a pass-through to the original function.
        # This lets us assert on the call/args and also implicitly ensures
        # that the email acutally renders as normal in send_mail.
        send_mail = mails.send_mail
        with mock.patch.object(listeners.mails, 'send_mail', side_effect=send_mail) as mock_send_mail:
            notify_submit(registration, admin)

        assert len(mock_send_mail.call_args_list) == 2
        admin_message, contrib_message = mock_send_mail.call_args_list

        assert admin_message == call(
            admin.email,
            mails.REVIEWS_SUBMISSION_CONFIRMATION,
            document_type='registration',
            domain='http://localhost:5000/',
            draft_registration=registration.draft_registration.get(),
            is_creator=True,
            logo='osf_registries',
            mimetype='html',
            no_future_emails=[],
            provider_contact_email=settings.OSF_CONTACT_EMAIL,
            provider_support_email=settings.OSF_SUPPORT_EMAIL,
            provider_name=provider.name,
            provider_url='http://localhost:5000/',
            referrer=admin,
            reviewable=registration,
            user=admin,
            workflow=None
        )

        assert contrib_message == call(
            contrib.email,
            mails.REVIEWS_SUBMISSION_CONFIRMATION,
            document_type='registration',
            domain='http://localhost:5000/',
            draft_registration=registration.draft_registration.get(),
            is_creator=False,
            logo='osf_registries',
            mimetype='html',
            no_future_emails=[],
            provider_contact_email=settings.OSF_CONTACT_EMAIL,
            provider_support_email=settings.OSF_SUPPORT_EMAIL,
            provider_name=provider.name,
            provider_url='http://localhost:5000/',
            referrer=admin,
            reviewable=registration,
            user=contrib,
            workflow=None
        )

        assert NotificationDigest.objects.count() == 1
        digest = NotificationDigest.objects.last()

        assert digest.user == moderator
        assert digest.send_type == 'email_transactional'
        assert digest.event == 'new_pending_submissions'

    def test_accept_notifications(self, registration, moderator, admin, contrib, accept_action):
        """
        [REQS-98] "As registration authors, we receive email notification upon moderator acceptance"
        :param draft_registration:
        :return:
        """
        add_reviews_notification_setting('global_reviews')

        # Set up mock_email as a pass-through to the original function.
        # This lets us assert on the call count/args and also implicitly
        # ensures that the email acutally renders correctly.
        store_emails = emails.store_emails
        with mock.patch.object(emails, 'store_emails', side_effect=store_emails) as mock_email:
            notify_accept_reject(registration, registration.creator, accept_action, RegistrationModerationStates)

        assert len(mock_email.call_args_list) == 2

        admin_message, contrib_message = mock_email.call_args_list

        assert admin_message == call(
            [admin._id],
            'email_transactional',
            'global_reviews',
            admin,
            registration,
            self.MOCK_NOW,
            comment='yo',
            document_type='registration',
            domain='http://localhost:5000/',
            draft_registration=registration.draft_registration.get(),
            has_psyarxiv_chronos_text=False,
            is_creator=True,
            is_rejected=False,
            notify_comment='yo',
            provider_contact_email=settings.OSF_CONTACT_EMAIL,
            provider_support_email=settings.OSF_SUPPORT_EMAIL,
            provider_url='http://localhost:5000/',
            requester=admin,
            reviewable=registration,
            template='reviews_submission_status',
            was_pending=False,
            workflow=None
        )

        assert contrib_message == call(
            [contrib._id],
            'email_transactional',
            'global_reviews',
            admin,
            registration,
            self.MOCK_NOW,
            comment='yo',
            document_type='registration',
            domain='http://localhost:5000/',
            draft_registration=registration.draft_registration.get(),
            has_psyarxiv_chronos_text=False,
            is_creator=False,
            is_rejected=False,
            notify_comment='yo',
            provider_contact_email=settings.OSF_CONTACT_EMAIL,
            provider_support_email=settings.OSF_SUPPORT_EMAIL,
            provider_url='http://localhost:5000/',
            reviewable=registration,
            requester=admin,
            template='reviews_submission_status',
            was_pending=False,
            workflow=None
        )

    def test_reject_notifications(self, registration, moderator, admin, contrib, accept_action):
        """
        [REQS-100] "As authors of rejected by moderator registration, we receive email notification of registration returned
        to draft state"
        :param draft_registration:
        :return:
        """
        add_reviews_notification_setting('global_reviews')

        # Set up mock_email as a pass-through to the original function.
        # This lets us assert on the call count/args and also implicitly
        # ensures that the email acutally renders correctly
        store_emails = emails.store_emails
        with mock.patch.object(emails, 'store_emails', side_effect=store_emails) as mock_email:
            notify_accept_reject(registration, registration.creator, accept_action, RegistrationModerationStates)

        assert len(mock_email.call_args_list) == 2

        admin_message, contrib_message = mock_email.call_args_list

        assert admin_message == call(
            [admin._id],
            'email_transactional',
            'global_reviews',
            admin,
            registration,
            self.MOCK_NOW,
            comment='yo',
            document_type='registration',
            domain='http://localhost:5000/',
            draft_registration=registration.draft_registration.get(),
            has_psyarxiv_chronos_text=False,
            is_creator=True,
            is_rejected=False,
            notify_comment='yo',
            provider_contact_email=settings.OSF_CONTACT_EMAIL,
            provider_support_email=settings.OSF_SUPPORT_EMAIL,
            provider_url='http://localhost:5000/',
            reviewable=registration,
            requester=admin,
            template='reviews_submission_status',
            was_pending=False,
            workflow=None
        )

        assert contrib_message == call(
            [contrib._id],
            'email_transactional',
            'global_reviews',
            admin,
            registration,
            self.MOCK_NOW,
            comment='yo',
            document_type='registration',
            domain='http://localhost:5000/',
            draft_registration=registration.draft_registration.get(),
            has_psyarxiv_chronos_text=False,
            is_creator=False,
            is_rejected=False,
            notify_comment='yo',
            provider_contact_email=settings.OSF_CONTACT_EMAIL,
            provider_support_email=settings.OSF_SUPPORT_EMAIL,
            provider_url='http://localhost:5000/',
            reviewable=registration,
            requester=admin,
            template='reviews_submission_status',
            was_pending=False,
            workflow=None
        )

    def test_notify_moderator_registration_requests_withdrawal_notifications(self, moderator, daily_moderator, registration, admin, provider):
        """
         [REQS-106] "As moderator, I receive registration withdrawal request notification email"

        :param mock_email:
        :param draft_registration:
        :param contrib:
        :return:
        """
        assert NotificationDigest.objects.count() == 0
        notify_moderator_registration_requests_withdrawal(registration, admin)

        assert NotificationDigest.objects.count() == 2

        daily_digest = NotificationDigest.objects.get(send_type='email_digest')
        transactional_digest = NotificationDigest.objects.get(send_type='email_transactional')
        assert daily_digest.user == daily_moderator
        assert transactional_digest.user == moderator

        for digest in (daily_digest, transactional_digest):
            assert 'requested withdrawal' in digest.message
            assert digest.event == 'new_pending_withdraw_requests'
            assert digest.provider == provider

    def test_withdrawal_registration_accepted_notifications(self, registration_with_retraction, contrib, admin, withdraw_action):
        """
        [REQS-109] "As registration author(s) requesting registration withdrawal, we receive notification email of moderator
        decision"

        :param mock_email:
        :param draft_registration:
        :param contrib:
        :return:
        """
        # Set up mock_send_mail as a pass-through to the original function.
        # This lets us assert on the call count/args and also implicitly
        # ensures that the email acutally renders as normal in send_mail.
        send_mail = mails.send_mail
        with mock.patch.object(machines.mails, 'send_mail', side_effect=send_mail) as mock_email:
            notify_withdraw_registration(registration_with_retraction, withdraw_action)

        assert len(mock_email.call_args_list) == 2
        admin_message, contrib_message = mock_email.call_args_list

        assert admin_message == call(
            admin.email,
            mails.WITHDRAWAL_REQUEST_GRANTED,
            comment='yo',
            contributor=admin,
            document_type='registration',
            domain='http://localhost:5000/',
            draft_registration=registration_with_retraction.draft_registration.get(),
            is_requester=True,
            force_withdrawal=False,
            notify_comment='yo',
            provider_contact_email=settings.OSF_CONTACT_EMAIL,
            provider_support_email=settings.OSF_SUPPORT_EMAIL,
            provider_url='http://localhost:5000/',
            requester=admin,
            reviewable=registration_with_retraction,
            workflow=None
        )

        assert contrib_message == call(
            contrib.email,
            mails.WITHDRAWAL_REQUEST_GRANTED,
            comment='yo',
            contributor=contrib,
            document_type='registration',
            domain='http://localhost:5000/',
            draft_registration=registration_with_retraction.draft_registration.get(),
            is_requester=False,
            force_withdrawal=False,
            notify_comment='yo',
            provider_contact_email=settings.OSF_CONTACT_EMAIL,
            provider_support_email=settings.OSF_SUPPORT_EMAIL,
            provider_url='http://localhost:5000/',
            requester=admin,
            reviewable=registration_with_retraction,
            workflow=None
        )

    def test_withdrawal_registration_rejected_notifications(self, registration, contrib, admin, withdraw_request_action):
        """
        [REQS-109] "As registration author(s) requesting registration withdrawal, we receive notification email of moderator
        decision"

        :param mock_email:
        :param draft_registration:
        :param contrib:
        :return:
        """
        # Set up mock_send_mail as a pass-through to the original function.
        # This lets us assert on the call count/args and also implicitly
        # ensures that the email acutally renders as normal in send_mail.
        send_mail = mails.send_mail
        with mock.patch.object(machines.mails, 'send_mail', side_effect=send_mail) as mock_email:
            notify_reject_withdraw_request(registration, withdraw_request_action)

        assert len(mock_email.call_args_list) == 2
        admin_message, contrib_message = mock_email.call_args_list

        assert admin_message == call(
            admin.email,
            mails.WITHDRAWAL_REQUEST_DECLINED,
            contributor=admin,
            document_type='registration',
            domain='http://localhost:5000/',
            draft_registration=registration.draft_registration.get(),
            is_requester=True,
            provider_contact_email=settings.OSF_CONTACT_EMAIL,
            provider_support_email=settings.OSF_SUPPORT_EMAIL,
            provider_url='http://localhost:5000/',
            requester=admin,
            reviewable=registration,
            workflow=None
        )

        assert contrib_message == call(
            contrib.email,
            mails.WITHDRAWAL_REQUEST_DECLINED,
            contributor=contrib,
            document_type='registration',
            domain='http://localhost:5000/',
            draft_registration=registration.draft_registration.get(),
            is_requester=False,
            provider_contact_email=settings.OSF_CONTACT_EMAIL,
            provider_support_email=settings.OSF_SUPPORT_EMAIL,
            provider_url='http://localhost:5000/',
            requester=admin,
            reviewable=registration,
            workflow=None
        )

    def test_withdrawal_registration_force_notifications(self, registration_with_retraction, contrib, admin, withdraw_action):
        """
        [REQS-109] "As registration author(s) requesting registration withdrawal, we receive notification email of moderator
        decision"

        :param mock_email:
        :param draft_registration:
        :param contrib:
        :return:
        """
        # Set up mock_send_mail as a pass-through to the original function.
        # This lets us assert on the call count/args and also implicitly
        # ensures that the email acutally renders as normal in send_mail.
        send_mail = mails.send_mail
        with mock.patch.object(machines.mails, 'send_mail', side_effect=send_mail) as mock_email:
            notify_withdraw_registration(registration_with_retraction, withdraw_action)

        assert len(mock_email.call_args_list) == 2
        admin_message, contrib_message = mock_email.call_args_list

        assert admin_message == call(
            admin.email,
            mails.WITHDRAWAL_REQUEST_GRANTED,
            comment='yo',
            contributor=admin,
            document_type='registration',
            domain='http://localhost:5000/',
            draft_registration=registration_with_retraction.draft_registration.get(),
            is_requester=True,
            force_withdrawal=False,
            notify_comment='yo',
            provider_contact_email=settings.OSF_CONTACT_EMAIL,
            provider_support_email=settings.OSF_SUPPORT_EMAIL,
            provider_url='http://localhost:5000/',
            requester=admin,
            reviewable=registration_with_retraction,
            workflow=None
        )

        assert contrib_message == call(
            contrib.email,
            mails.WITHDRAWAL_REQUEST_GRANTED,
            comment='yo',
            contributor=contrib,
            document_type='registration',
            domain='http://localhost:5000/',
            draft_registration=registration_with_retraction.draft_registration.get(),
            is_requester=False,
            force_withdrawal=False,
            notify_comment='yo',
            provider_contact_email=settings.OSF_CONTACT_EMAIL,
            provider_support_email=settings.OSF_SUPPORT_EMAIL,
            provider_url='http://localhost:5000/',
            requester=admin,
            reviewable=registration_with_retraction,
            workflow=None
        )

    @pytest.mark.parametrize(
        'digest_type, expected_recipient',
        [('email_transactional', moderator), ('email_digest', daily_moderator)]
    )
    def test_submissions_and_withdrawals_both_appear_in_moderator_digest(self, digest_type, expected_recipient, registration, admin, provider):
        # Invoke the fixture function to get the recipient because parametrize
        expected_recipient = expected_recipient(self, provider)
        notify_submit(registration, admin)
        notify_moderator_registration_requests_withdrawal(registration, admin)

        # One user, one provider => one email
        grouped_notifications = list(tasks.get_moderators_emails(digest_type))
        assert len(grouped_notifications) == 1

        moderator_message = grouped_notifications[0]
        assert moderator_message['user_id'] == expected_recipient._id
        assert moderator_message['provider_id'] == provider.id

        # No fixed ordering of the entires, so just make sure that
        # keywords for each action type are in some message
        updates = moderator_message['info']
        assert len(updates) == 2
        assert any('submitted' in entry['message'] for entry in updates)
        assert any('requested withdrawal' in entry['message'] for entry in updates)

    @pytest.mark.parametrize('digest_type', ['email_transactional', 'email_digest'])
    def test_submsissions_and_withdrawals_do_not_appear_in_node_digest(self, digest_type, registration, admin, moderator, daily_moderator):
        notify_submit(registration, admin)
        notify_moderator_registration_requests_withdrawal(registration, admin)

        assert not list(tasks.get_users_emails(digest_type))

    def test_moderator_digest_emails_render(self, registration, admin, moderator):
        notify_moderator_registration_requests_withdrawal(registration, admin)
        # Set up mock_send_mail as a pass-through to the original function.
        # This lets us assert on the call count/args and also implicitly
        # ensures that the email acutally renders as normal in send_mail.
        send_mail = mails.send_mail
        with mock.patch.object(tasks.mails, 'send_mail', side_effect=send_mail) as mock_send_mail:
            tasks._send_reviews_moderator_emails('email_transactional')

        mock_send_mail.assert_called()

    def test_branded_provider_notification_renders(self, registration, admin, moderator):
        # Set brand details to be checked in notify_base.mako
        provider = registration.provider
        provider.brand = Brand.objects.create(hero_logo_image='not-a-url', primary_color='#FFA500')
        provider.name = 'Test Provider'
        provider.save()

        # Implicitly check that all of our uses of notify_base.mako render with branded details:
        #
        # notify_submit renders reviews_submission_confirmation using context from
        # osf.utils.notifications and stores emails to be picked up in the moderator digest
        #
        # _send_Reviews_moderator_emails renders digest_reviews_moderators using context from
        # website.notifications.tasks
        notify_submit(registration, admin)
        tasks._send_reviews_moderator_emails('email_transactional')
        assert True  # everything rendered!
