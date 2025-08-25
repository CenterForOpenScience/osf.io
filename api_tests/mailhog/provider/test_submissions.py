import pytest
from waffle.testutils import override_switch
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

from osf.models import NotificationType

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
        assert notifications['emits'][0]['type'] == NotificationType.Type.PROVIDER_NEW_PENDING_WITHDRAW_REQUESTS
        assert notifications['emits'][1]['type'] == NotificationType.Type.PROVIDER_NEW_PENDING_WITHDRAW_REQUESTS
        massages = get_mailhog_messages()
        assert massages['count'] == len(notifications['emails'])
        assert_emails(massages, notifications)

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
        delete_mailhog_messages()
        with capture_notifications(passthrough=True) as notifications:

            registration.require_approval(user=registration.creator)
            approval = registration.registration_approval
            approval.approve(
                user=registration.creator,
                token=approval.token_for_user(registration.creator, 'approval')
            )

            resp = app.get(provider_actions_url, auth=moderator.auth)

        assert len(notifications['emits']) == 3
        assert notifications['emits'][0]['type'] == NotificationType.Type.PROVIDER_REVIEWS_SUBMISSION_CONFIRMATION
        assert notifications['emits'][1]['type'] == NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS
        assert notifications['emits'][2]['type'] == NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS
        massages = get_mailhog_messages()
        assert massages['count'] == len(notifications['emails'])
        assert_emails(massages, notifications)

        delete_mailhog_messages()

        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['attributes']['trigger'] == RegistrationModerationTriggers.SUBMIT.db_name
        assert resp.json['data'][0]['relationships']['creator']['data']['id'] == registration.creator._id
