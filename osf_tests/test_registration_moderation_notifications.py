import pytest
import mock
from mock import call
import datetime

from osf.management.commands.add_notification_subscription import add_reviews_notification_setting
from osf.migrations import update_provider_auth_groups
from osf.models import NotificationDigest
from website.profile.utils import get_profile_image_url

from osf_tests.factories import (
    RegistrationFactory,
    AuthUserFactory
)

from unittest.mock import ANY

from website import mails, settings

from osf.utils.workflows import RegistrationStates

@pytest.mark.django_db
class TestRegistrationMachineNotification:

    MOCK_NOW = datetime.datetime(2018, 2, 4)

    @pytest.yield_fixture(autouse=True)
    def time_machine(self):
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
    def provider(self, registration):
        return registration.provider

    @pytest.fixture()
    def moderator(self, provider):
        user = AuthUserFactory()
        provider.add_to_group(user, 'moderator')
        return user

    def test_submit_notifications(self, registration, moderator, admin, contrib, provider):
        """
        "As moderator of branded registry, I receive email notification upon admin author(s) submission approval"
        :param mock_email:
        :param draft_registration:
        :return:
        """
        registration.moderation_state = RegistrationStates.SUBMIT.value
        registration.update_moderation_state()

        with mock.patch('website.reviews.listeners.mails.send_mail') as mock_send_mail:
            registration.run_submit(admin)

        assert len(mock_send_mail.call_args_list) == 1

        mock_send_mail.assert_called_with(
            admin.email,
            mails.REVIEWS_SUBMISSION_CONFIRMATION,
            document_type='registrations',
            domain='http://localhost:5000/',
            is_creator=True,
            logo='osf_registries',
            mimetype='html',
            no_future_emails=[],
            provider_contact_email=settings.OSF_CONTACT_EMAIL,
            provider_support_email=settings.OSF_SUPPORT_EMAIL,
            provider_name=provider.name,
            provider_url='http://localhost:5000/',
            referrer=admin,
            requester=admin,
            reviewable=registration,
            user=admin,
            workflow=None
        )

        notification = NotificationDigest.objects.all()[0]

        assert notification.user == moderator
        assert notification.send_type == 'email_transactional'
        assert notification.event == 'new_pending_submissions'

    def test_run_accept_notifications(self, draft_registration, moderator, admin, contrib):
        """
        "As registration authors, we receive email notification upon moderator acceptance"
        :param draft_registration:
        :return:
        """
        add_reviews_notification_setting('global_reviews')

        draft_registration.run_submit(admin)
        with mock.patch('website.notifications.emails.store_emails') as mock_email:
            draft_registration.run_accept(admin, 'yo')

        assert len(mock_email.call_args_list) == 2

        admin_message, contrib_message = mock_email.call_args_list

        assert admin_message == call(
            [admin._id],
            'email_transactional',
            'global_reviews',
            admin,
            draft_registration.registered_node,
            self.MOCK_NOW,
            comment='yo',
            document_type='registrations',
            domain='http://localhost:5000/',
            has_psyarxiv_chronos_text=False,
            is_creator=True,
            is_rejected=False,
            notify_comment='yo',
            provider_contact_email=settings.OSF_CONTACT_EMAIL,
            provider_support_email=settings.OSF_SUPPORT_EMAIL,
            provider_url='http://localhost:5000/',
            reviewable=draft_registration.registered_node,
            template='reviews_submission_status',
            was_pending=True,
            requester=admin,
            workflow=None
        )

        assert contrib_message == call(
            [contrib._id],
            'email_transactional',
            'global_reviews',
            admin,
            draft_registration.registered_node,
            self.MOCK_NOW,
            comment='yo',
            document_type='registrations',
            domain='http://localhost:5000/',
            has_psyarxiv_chronos_text=False,
            is_creator=False,
            is_rejected=False,
            notify_comment='yo',
            provider_contact_email=settings.OSF_CONTACT_EMAIL,
            provider_support_email=settings.OSF_SUPPORT_EMAIL,
            provider_url='http://localhost:5000/',
            reviewable=draft_registration.registered_node,
            template='reviews_submission_status',
            was_pending=True,
            requester=admin,
            workflow=None
        )

    def test_reject_notifications(self, draft_registration, moderator, admin, contrib):
        """
        "As authors of rejected by moderator registration, we receive email notification of registration returned
        to draft state"
        :param draft_registration:
        :return:
        """
        add_reviews_notification_setting('global_reviews')

        draft_registration.run_submit(admin)
        with mock.patch('website.notifications.emails.store_emails') as mock_email:
            draft_registration.run_reject(admin, 'yo')

        assert len(mock_email.call_args_list) == 2

        admin_message, contrib_message = mock_email.call_args_list

        assert admin_message == call(
            [admin._id],
            'email_transactional',
            'global_reviews',
            admin,
            draft_registration.registered_node,
            self.MOCK_NOW,
            comment='yo',
            document_type='registrations',
            domain='http://localhost:5000/',
            has_psyarxiv_chronos_text=False,
            is_creator=True,
            is_rejected=True,
            notify_comment='yo',
            provider_contact_email=settings.OSF_CONTACT_EMAIL,
            provider_support_email=settings.OSF_SUPPORT_EMAIL,
            provider_url='http://localhost:5000/',
            reviewable=draft_registration.registered_node,
            template='reviews_submission_status',
            was_pending=True,
            requester=admin,
            workflow=None
        )

        assert contrib_message == call(
            [contrib._id],
            'email_transactional',
            'global_reviews',
            admin,
            draft_registration.registered_node,
            self.MOCK_NOW,
            comment='yo',
            document_type='registrations',
            domain='http://localhost:5000/',
            has_psyarxiv_chronos_text=False,
            is_creator=False,
            is_rejected=True,
            notify_comment='yo',
            provider_contact_email=settings.OSF_CONTACT_EMAIL,
            provider_support_email=settings.OSF_SUPPORT_EMAIL,
            provider_url='http://localhost:5000/',
            reviewable=draft_registration.registered_node,
            template='reviews_submission_status',
            was_pending=True,
            requester=admin,
            workflow=None
        )

    def test_run_request_embargo_termination(self, draft_registration, admin):
        add_reviews_notification_setting('global_reviews')

        draft_registration.run_submit(admin)
        draft_registration.run_accept(
            admin,
            'yo',
            embargo_end_date=datetime.datetime(2020, 2, 4)
        )

        # Contributors confirm embargo
        embargo = draft_registration.registered_node.embargo
        embargo.state = 'approved'
        embargo.save()

        with mock.patch('osf.models.sanctions.mails.send_mail') as mock_email:
            draft_registration.run_request_embargo_termination(admin, 'yo')

        assert len(mock_email.call_args_list) == 1
        transactional = mock_email.call_args_list[0]

        assert transactional == call(
            admin.email,
            mails.PENDING_EMBARGO_TERMINATION_ADMIN,
            approval_link=ANY,
            approval_time_span=48,
            can_change_preferences=False,
            disapproval_link=ANY,
            embargo_end_date=None,
            initiated_by=admin.fullname,
            is_initiator=True,
            project_name=draft_registration.registered_node.title,
            registration_link=f'http://localhost:5000/{draft_registration.registered_node._id}/',
            user=admin
        )

    def test_run_request_withdrawal_notifications(self, draft_registration, contrib, admin, moderator):
        """
        "As admin(s) on pending withdrawal registration, I receive an email to approve/cancel my withdrawal within
         48hrs."
        :param mock_email:
        :param draft_registration:
        :param contrib:
        :return:
        """
        draft_registration.run_submit(admin)
        draft_registration.run_accept(admin, 'yo')
        draft_registration.registered_node.is_public = True
        draft_registration.registered_node.save()

        with mock.patch('osf.models.sanctions.mails.send_mail') as mock_email:
            draft_registration.run_request_withdraw(admin, 'yo')

        assert len(mock_email.call_args_list) == 2
        admin_message, contrib_message = mock_email.call_args_list

        assert admin_message == call(
            admin.email,
            mails.PENDING_RETRACTION_ADMIN,
            approval_link=ANY,
            approval_time_span=48,
            can_change_preferences=False,
            disapproval_link=ANY,
            initiated_by=admin.fullname,
            is_initiator=True,
            project_name=draft_registration.registered_node.title,
            registration_link=f'http://localhost:5000/{draft_registration.registered_node._id}/',
            user=admin
        )

        assert contrib_message == call(
            contrib.email,
            mails.PENDING_RETRACTION_NON_ADMIN,
            can_change_preferences=False,
            initiated_by=admin.fullname,
            registration_link=f'http://localhost:5000/{draft_registration.registered_node._id}/',
            user=contrib
        )

    def test_run_withdrawal_registration_accepted_notifications(self, draft_registration, contrib, admin, moderator, provider):
        """
         "As moderator, I receive registration withdrawal request notification email"

        :param mock_email:
        :param draft_registration:
        :param contrib:
        :return:
        """
        add_reviews_notification_setting('global_reviews')
        add_reviews_notification_setting('new_pending_submissions')
        add_reviews_notification_setting('new_pending_withdraw_requests')

        draft_registration.run_submit(admin)
        draft_registration.run_accept(admin, 'yo')
        draft_registration.registered_node.is_public = True
        draft_registration.registered_node.save()
        draft_registration.run_request_withdraw(admin, 'yo')

        with mock.patch('website.notifications.emails.store_emails') as mock_email:
            draft_registration.run_request_withdraw_passes(admin, 'yo')

        assert len(mock_email.call_args_list) == 1

        transactional = mock_email.call_args_list[0]

        assert transactional == call(
            [moderator._id],
            'email_transactional',
            'new_pending_withdraw_requests',
            admin,
            draft_registration.registered_node,
            self.MOCK_NOW,
            abstract_provider=draft_registration.provider,
            document_type='registrations',
            domain='http://localhost:5000/',
            message=f'submitted "{draft_registration.registered_node.title}".',
            profile_image_url=get_profile_image_url(admin),
            provider_contact_email=settings.OSF_CONTACT_EMAIL,
            provider_support_email=settings.OSF_SUPPORT_EMAIL,
            provider_url='http://localhost:5000/',
            referrer=admin,
            requester=admin,
            reviewable=draft_registration.registered_node,
            reviews_submission_url=f'http://localhost:5000/reviews/registries/osf/{draft_registration.registered_node._id}',
            workflow=None
        )

    def test_run_withdrawal_registration_rejected_notifications(self, draft_registration, contrib, admin):
        """
        "As registration author(s) requesting registration withdrawal, we receive notification email of moderator
        decision"

        :param mock_email:
        :param draft_registration:
        :param contrib:
        :return:
        """
        draft_registration.run_submit(admin)
        draft_registration.run_accept(admin, 'yo')
        draft_registration.registered_node.is_public = True
        draft_registration.registered_node.save()
        draft_registration.run_request_withdraw(draft_registration.creator, 'yo')
        draft_registration.run_request_withdraw_passes(admin, 'yo')

        with mock.patch('osf.utils.machines.mails.send_mail') as mock_email:
            draft_registration.run_reject_withdraw(admin, 'yo')

        assert len(mock_email.call_args_list) == 2
        admin_message, contrib_message = mock_email.call_args_list

        assert admin_message == call(
            admin.email,
            mails.WITHDRAWAL_REQUEST_DECLINED,
            contributor=admin,
            document_type='registrations',
            domain='http://localhost:5000/',
            is_requester=True,
            mimetype='html',
            provider_contact_email=settings.OSF_CONTACT_EMAIL,
            provider_support_email=settings.OSF_SUPPORT_EMAIL,
            provider_url='http://localhost:5000/',
            requester=admin,
            reviewable=draft_registration.registered_node,
            workflow=None
        )

        assert contrib_message == call(
            contrib.email,
            mails.WITHDRAWAL_REQUEST_DECLINED,
            contributor=contrib,
            document_type='registrations',
            domain='http://localhost:5000/',
            is_requester=False,
            mimetype='html',
            provider_contact_email=settings.OSF_CONTACT_EMAIL,
            provider_support_email=settings.OSF_SUPPORT_EMAIL,
            provider_url='http://localhost:5000/',
            requester=admin,
            reviewable=draft_registration.registered_node,
            workflow=None
        )

    def test_run_withdrawal_registration_notifications(self, draft_registration, contrib, admin):
        """
        "As registration author(s) requesting registration withdrawal, we receive notification email of moderator
        decision"

        :param mock_email:
        :param draft_registration:
        :param contrib:
        :return:
        """
        draft_registration.run_submit(admin)
        draft_registration.run_accept(admin, 'yo')
        draft_registration.registered_node.is_public = True
        draft_registration.registered_node.save()
        draft_registration.run_request_withdraw(admin, 'yo')
        draft_registration.run_request_withdraw_passes(admin, 'yo')

        with mock.patch('osf.utils.machines.mails.send_mail') as mock_email:
            draft_registration.run_withdraw_registration(admin, 'yo')

        assert len(mock_email.call_args_list) == 2
        admin_message, contrib_message = mock_email.call_args_list

        assert admin_message == call(
            admin.email,
            mails.WITHDRAWAL_REQUEST_GRANTED,
            contributor=admin,
            document_type='registrations',
            domain='http://localhost:5000/',
            is_requester=True,
            mimetype='html',
            provider_contact_email=settings.OSF_CONTACT_EMAIL,
            provider_support_email=settings.OSF_SUPPORT_EMAIL,
            provider_url='http://localhost:5000/',
            reviewable=draft_registration.registered_node,
            requester=admin,
            user=admin,
            workflow=None
        )

        assert contrib_message == call(
            contrib.email,
            mails.WITHDRAWAL_REQUEST_GRANTED,
            contributor=contrib,
            document_type='registrations',
            domain='http://localhost:5000/',
            is_requester=False,
            mimetype='html',
            provider_contact_email=settings.OSF_CONTACT_EMAIL,
            provider_support_email=settings.OSF_SUPPORT_EMAIL,
            provider_url='http://localhost:5000/',
            reviewable=draft_registration.registered_node,
            requester=admin,
            user=contrib,
            workflow=None
        )
