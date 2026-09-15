import pytest
from waffle.testutils import override_switch

from notifications.tasks import send_users_instant_digest_email
from osf import features

from api.base.settings.defaults import API_BASE

from api.providers.workflows import Workflows
from osf.utils.workflows import RegistrationModerationTriggers

from osf_tests.factories import (
    AuthUserFactory,
    RegistrationFactory,
    RegistrationProviderFactory,
)


from tests.base import get_default_metaschema

from osf.models import NotificationTypeEnum, Notification

from osf.migrations import update_provider_auth_groups
from tests.utils import capture_notifications, get_mailhog_messages, delete_mailhog_messages, assert_emails


@pytest.mark.django_db
class TestRegistriesModerationSubmissions:

    @pytest.fixture()
    def moderator(self):
        return AuthUserFactory()

    @pytest.fixture()
    def provider(self, moderator):
        provider = RegistrationProviderFactory()
        update_provider_auth_groups()
        provider.schemas.add(get_default_metaschema())
        provider.get_group('moderator').user_set.add(moderator)
        provider.reviews_workflow = Workflows.PRE_MODERATION.value

        provider.save()

        return provider

    @pytest.fixture()
    def reg_creator(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration(self, provider, reg_creator):
        return RegistrationFactory(provider=provider, creator=reg_creator)

    @pytest.fixture()
    def provider_actions_url(self, provider):
        return f'/{API_BASE}providers/registrations/{provider._id}/actions/'

    @pytest.fixture()
    def registration_actions_url(self, registration):
        return f'/{API_BASE}registrations/{registration._id}/actions/'

    @override_switch(features.ENABLE_MAILHOG, active=True)
    def test_get_registration_actions(self, app, registration_actions_url, registration, moderator):
        resp = app.get(registration_actions_url, expect_errors=True)
        assert resp.status_code == 401

        resp = app.get(registration_actions_url, auth=moderator.auth)

        assert resp.status_code == 200
        assert len(resp.json['data']) == 0

        delete_mailhog_messages()
        with capture_notifications(passthrough=True) as notifications:
            registration.is_public = True
            retraction = registration.retract_registration(
                user=registration.creator, justification='because')
            retraction.approve(
                user=registration.creator,
                token=retraction.token_for_user(registration.creator, 'approval')
            )
            registration.save()
            resp = app.get(registration_actions_url, auth=moderator.auth)

        assert len(notifications['emits']) == 2
        assert notifications['emits'][0]['type'] == NotificationTypeEnum.PROVIDER_NEW_PENDING_WITHDRAW_REQUESTS
        assert notifications['emits'][1]['type'] == NotificationTypeEnum.PROVIDER_NEW_PENDING_WITHDRAW_REQUESTS
        messages = get_mailhog_messages()
        assert_emails(messages, notifications)

        delete_mailhog_messages()

        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['attributes']['trigger'] == RegistrationModerationTriggers.REQUEST_WITHDRAWAL.db_name
        assert resp.json['data'][0]['relationships']['creator']['data']['id'] == registration.creator._id

    @override_switch(features.ENABLE_MAILHOG, active=True)
    def test_get_provider_actions(self, app, provider_actions_url, registration, moderator):
        resp = app.get(provider_actions_url, expect_errors=True)
        assert resp.status_code == 401

        resp = app.get(provider_actions_url, auth=moderator.auth)
        assert resp.status_code == 200
        assert len(resp.json['data']) == 0
        # registration fixture asks the creator for approval
        assert Notification.objects.count() == 1

        another_contributor = AuthUserFactory()
        registration.add_contributor(another_contributor, permissions='admin', visible=True)

        delete_mailhog_messages()
        with capture_notifications(passthrough=True) as notifications:
            # 2 notifications: creator and another contributor are notified of node_pending_registration_admin
            registration.require_approval(user=registration.creator)
            approval = registration.registration_approval
            # approve the registration to trigger the notification to the provider moderators
            # 2 notifications: creator and another contributor are notified of provider_reviews_submission_confirmation
            approval.approve(
                user=registration.creator,
                token=approval.token_for_user(registration.creator, 'approval')
            )
            approval.approve(
                user=another_contributor,
                token=approval.token_for_user(another_contributor, 'approval')
            )
            # 1 notification after all approvals: provider moderator is notified about provider_new_pending_submissions
            resp = app.get(provider_actions_url, auth=moderator.auth)

        assert len(notifications['emits']) == 5

        notifications = [(notification['kwargs']['user'], notification['type']) for notification in notifications['emits']]
        assert (registration.creator, NotificationTypeEnum.NODE_PENDING_REGISTRATION_ADMIN) in notifications
        assert (another_contributor, NotificationTypeEnum.NODE_PENDING_REGISTRATION_ADMIN) in notifications
        assert (registration.creator, NotificationTypeEnum.PROVIDER_REVIEWS_SUBMISSION_CONFIRMATION) in notifications
        assert (another_contributor, NotificationTypeEnum.PROVIDER_REVIEWS_SUBMISSION_CONFIRMATION) in notifications
        assert (moderator, NotificationTypeEnum.PROVIDER_NEW_PENDING_SUBMISSIONS) in notifications

        send_users_instant_digest_email.delay()
        messages = get_mailhog_messages()
        assert messages['count'] == 4

        # actions within capture_notifications triggered registration approval + submission confirmation emails
        user_and_email_type = [(message['Content']['Headers']['To'][0], message['Content']['Headers']['Subject'][0]) for message in messages['items']]
        assert (registration.creator.username, 'Pending Registration - Admin Notification') in user_and_email_type
        assert (another_contributor.username, 'Pending Registration - Admin Notification') in user_and_email_type
        assert (registration.creator.username, 'Submission Confirmation') in user_and_email_type
        assert (another_contributor.username, 'Submission Confirmation') in user_and_email_type

        delete_mailhog_messages()

        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['attributes']['trigger'] == RegistrationModerationTriggers.SUBMIT.db_name
        assert resp.json['data'][0]['relationships']['creator']['data']['id'] == registration.creator._id
