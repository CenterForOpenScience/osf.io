import pytest
from api.base.settings.defaults import API_BASE
from api.providers.workflows import Workflows
from osf.utils.workflows import RequestTypes, RegistrationModerationTriggers, RegistrationModerationStates


from osf_tests.factories import (
    AuthUserFactory,
    RegistrationFactory,
    RegistrationProviderFactory,
    NodeRequestFactory
)
from tests.base import get_default_metaschema

from osf.models import NodeRequest, Registration

from osf.migrations import update_provider_auth_groups


@pytest.mark.django_db
class TestRegistriesModerationSubmissions:

    @pytest.fixture()
    def moderator(self):
        return AuthUserFactory()

    @pytest.fixture()
    def moderator_wrong_provider(self):
        user = AuthUserFactory()
        provider = RegistrationProviderFactory()
        update_provider_auth_groups()
        provider.schemas.add(get_default_metaschema())
        provider.get_group('moderator').user_set.add(user)
        provider.save()

        return user

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
    def registration_with_withdraw_request(self, provider):
        registration = RegistrationFactory(provider=provider)

        NodeRequest.objects.create(
            request_type=RequestTypes.WITHDRAWAL.value,
            target=registration,
            creator=registration.creator
        )

        return registration

    @pytest.fixture()
    def access_request(self, provider):
        request = NodeRequestFactory(request_type=RequestTypes.ACCESS.value)
        request.target.provider = provider
        request.target.save()

        return request

    @pytest.fixture()
    def registration(self, provider):
        return RegistrationFactory(provider=provider)

    @pytest.fixture(autouse=True)
    def unapproved_registration(self, provider):
        """ As far as registries moderation goes these unapproved registration should be invisible."""
        reg = Registration(title='Test title', provider=provider)
        reg.save()
        return reg

    @pytest.fixture()
    def provider_requests_url(self, provider):
        return f'/{API_BASE}providers/registrations/{provider._id}/requests/'

    @pytest.fixture()
    def registration_requests_url(self, registration_with_withdraw_request):
        return f'/{API_BASE}registrations/{registration_with_withdraw_request._id}/requests/'

    @pytest.fixture()
    def registrations_url(self, provider):
        return f'/{API_BASE}providers/registrations/{provider._id}/registrations/'

    @pytest.fixture()
    def registration_detail_url(self, registration):
        return f'/{API_BASE}registrations/{registration._id}/'

    @pytest.fixture()
    def registration_log_url(self, registration):
        return f'/{API_BASE}registrations/{registration._id}/logs/'

    @pytest.fixture()
    def provider_actions_url(self, provider):
        return f'/{API_BASE}providers/registrations/{provider._id}/actions/'

    @pytest.fixture()
    def registration_actions_url(self, registration):
        return f'/{API_BASE}registrations/{registration._id}/actions/'

    def test_get_provider_requests(self, app, provider_requests_url, registration_with_withdraw_request, access_request, moderator, moderator_wrong_provider):
        resp = app.get(provider_requests_url, expect_errors=True)
        assert resp.status_code == 401

        resp = app.get(provider_requests_url, auth=moderator_wrong_provider.auth, expect_errors=True)
        assert resp.status_code == 403

        resp = app.get(provider_requests_url, auth=moderator.auth)

        assert resp.status_code == 200
        assert len(resp.json['data']) == 2

        resp = app.get(f'{provider_requests_url}?filter[request_type]=withdrawal', auth=moderator.auth)

        assert resp.status_code == 200
        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['relationships']['target']['data']['id'] == registration_with_withdraw_request._id

    def test_get_registration_requests(self, app, registration_requests_url, registration_with_withdraw_request, access_request, moderator, moderator_wrong_provider):
        resp = app.get(registration_requests_url, expect_errors=True)
        assert resp.status_code == 401

        resp = app.get(registration_requests_url, auth=moderator_wrong_provider.auth, expect_errors=True)
        assert resp.status_code == 403

        resp = app.get(registration_requests_url, auth=moderator.auth)

        assert resp.status_code == 200
        assert len(resp.json['data']) == 1

        resp = app.get(f'{registration_requests_url}?filter[request_type]=withdrawal', auth=moderator.auth)

        assert resp.status_code == 200
        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['relationships']['target']['data']['id'] == registration_with_withdraw_request._id

    def test_get_registrations(self, app, registrations_url, registration, moderator, moderator_wrong_provider):
        resp = app.get(registrations_url, expect_errors=True)
        assert resp.status_code == 401

        resp = app.get(registrations_url, auth=moderator_wrong_provider.auth, expect_errors=True)
        assert resp.status_code == 403

        resp = app.get(registrations_url, auth=moderator.auth)

        assert resp.status_code == 200
        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['id'] == registration._id
        assert resp.json['data'][0]['attributes']['machine_state'] == RegistrationModerationStates.INITIAL.db_name
        assert resp.json['data'][0]['relationships']['requests']
        assert resp.json['data'][0]['relationships']['review_actions']

    def test_get_registrations_machine_state_filter(self, app, registrations_url, registration, moderator):

        resp = app.get(f'{registrations_url}?filter[machine_state]=initial', auth=moderator.auth)

        assert resp.status_code == 200
        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['id'] == registration._id

        resp = app.get(f'{registrations_url}?filter[machine_state]=pending', auth=moderator.auth)

        assert resp.status_code == 200
        assert len(resp.json['data']) == 0

        approval = registration.registration_approval
        approval.approve(
            user=registration.creator,
            token=approval.token_for_user(registration.creator, 'approval')
        )

        resp = app.get(f'{registrations_url}?filter[machine_state]=pending&meta[reviews_state_counts]=true', auth=moderator.auth)

        assert resp.status_code == 200
        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['id'] == registration._id
        assert resp.json['data'][0]['attributes']['machine_state'] == RegistrationModerationStates.PENDING.db_name
        assert resp.json['meta']['reviews_state_counts']['pending'] == 1

    @pytest.mark.enable_quickfiles_creation
    def test_get_registration_actions(self, app, registration_actions_url, registration, moderator):
        resp = app.get(registration_actions_url, expect_errors=True)
        assert resp.status_code == 401

        resp = app.get(registration_actions_url, auth=moderator.auth)

        assert resp.status_code == 200
        assert len(resp.json['data']) == 0

        registration.is_public = True
        retraction = registration.retract_registration(
            user=registration.creator, justification='because')
        retraction.approve(
            user=registration.creator,
            token=retraction.token_for_user(registration.creator, 'approval')
        )
        registration.save()

        resp = app.get(registration_actions_url, auth=moderator.auth)

        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['attributes']['trigger'] == RegistrationModerationTriggers.REQUEST_WITHDRAWAL.db_name
        assert resp.json['data'][0]['relationships']['creator']['data']['id'] == registration.creator._id

    @pytest.mark.enable_quickfiles_creation
    def test_get_provider_actions(self, app, provider_actions_url, registration, moderator):
        resp = app.get(provider_actions_url, expect_errors=True)
        assert resp.status_code == 401

        resp = app.get(provider_actions_url, auth=moderator.auth)

        assert resp.status_code == 200
        assert len(resp.json['data']) == 0

        registration.require_approval(user=registration.creator)
        approval = registration.registration_approval
        approval.approve(
            user=registration.creator,
            token=approval.token_for_user(registration.creator, 'approval')
        )

        resp = app.get(provider_actions_url, auth=moderator.auth)

        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['attributes']['trigger'] == RegistrationModerationTriggers.SUBMIT.db_name
        assert resp.json['data'][0]['relationships']['creator']['data']['id'] == registration.creator._id

    def test_registries_moderation_permission(self, app, registration_detail_url, registration, moderator, moderator_wrong_provider):
        resp = app.get(registration_detail_url, expect_errors=True)
        assert resp.status_code == 401

        resp = app.get(registration_detail_url, auth=moderator_wrong_provider.auth, expect_errors=True)
        assert resp.status_code == 403

        resp = app.get(registration_detail_url, auth=moderator.auth)
        assert resp.status_code == 200

    def test_registries_moderation_permission_log(self, app, registration_log_url, registration, moderator, moderator_wrong_provider):
        resp = app.get(registration_log_url, expect_errors=True)
        assert resp.status_code == 401

        resp = app.get(registration_log_url, auth=moderator_wrong_provider.auth, expect_errors=True)
        assert resp.status_code == 403

        resp = app.get(registration_log_url, auth=moderator.auth)
        assert resp.status_code == 200
