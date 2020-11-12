import pytest
import datetime

from api.base.settings.defaults import API_BASE

from api.providers.workflows import Workflows
from osf.utils.workflows import RequestTypes, RegistrationModerationTriggers, RegistrationModerationStates


from osf_tests.factories import (
    AuthUserFactory,
    RegistrationFactory,
    RegistrationProviderFactory,
    NodeRequestFactory,
    EmbargoFactory,
    RetractionFactory,
)


from tests.base import get_default_metaschema

from osf.models import NodeRequest

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
    def admin(self, provider):
        user = AuthUserFactory()
        provider.get_group('admin').user_set.add(user)
        provider.save()
        return user

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
    def reg_creator(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration(self, provider, reg_creator):
        return RegistrationFactory(provider=provider, creator=reg_creator)

    @pytest.fixture()
    def embargo_registration(self, provider, reg_creator):
        one_month_from_now = datetime.datetime.now() + datetime.timedelta(days=30)
        embargo = EmbargoFactory(end_date=one_month_from_now, user=reg_creator)
        registration = embargo.target_registration
        registration.provider = provider
        registration.update_moderation_state()
        registration.save()
        return registration

    @pytest.fixture()
    def retract_registration(self, provider, reg_creator):
        retract = RetractionFactory(user=reg_creator)
        registration = retract.target_registration
        registration.provider = provider
        registration.update_moderation_state()
        registration.save()
        return registration

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

    @pytest.fixture()
    def embargo_registration_actions_url(self, embargo_registration):
        return f'/{API_BASE}registrations/{embargo_registration._id}/actions/'

    @pytest.fixture()
    def retract_registration_actions_url(self, retract_registration):
        return f'/{API_BASE}registrations/{retract_registration._id}/actions/'

    @pytest.fixture()
    def actions_payload_base(self):
        payload = {
            'data': {
                'attributes': {
                },
                'relationships': {
                    'target': {
                        'data': {
                            'type': 'registrations'
                        }
                    }
                },
                'type': 'registration-actions'
            }
        }
        return payload

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
        assert resp.json['data'][0]['attributes']['reviews_state'] == RegistrationModerationStates.INITIAL.db_name
        assert resp.json['data'][0]['relationships']['requests']
        assert resp.json['data'][0]['relationships']['review_actions']

    def test_get_registrations_reviews_state_filter(self, app, registrations_url, registration, moderator):

        resp = app.get(f'{registrations_url}?filter[reviews_state]=initial', auth=moderator.auth)

        assert resp.status_code == 200
        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['id'] == registration._id

        resp = app.get(f'{registrations_url}?filter[reviews_state]=accepted', auth=moderator.auth)

        assert resp.status_code == 200
        assert len(resp.json['data']) == 0

        # RegistrationFactory auto-approves the initial RegistrationApproval
        registration.update_moderation_state()

        resp = app.get(f'{registrations_url}?filter[reviews_state]=accepted&meta[reviews_state_counts]=true', auth=moderator.auth)

        assert resp.status_code == 200
        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['id'] == registration._id
        assert resp.json['data'][0]['attributes']['reviews_state'] == RegistrationModerationStates.ACCEPTED.db_name
        assert resp.json['meta']['reviews_state_counts']['accepted'] == 1

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
        # Moderators should be able to view registration details once the registration is pending
        registration.moderation_state = RegistrationModerationStates.PENDING.db_name
        registration.save()
        resp = app.get(registration_detail_url, expect_errors=True)
        assert resp.status_code == 401

        resp = app.get(registration_detail_url, auth=moderator_wrong_provider.auth, expect_errors=True)
        assert resp.status_code == 403

        resp = app.get(registration_detail_url, auth=moderator.auth)
        assert resp.status_code == 200

    def test_registries_moderation_permission_log(self, app, registration_log_url, registration, moderator, moderator_wrong_provider):
        # Moderators should be able to view registration logs once the registration is pending
        registration.moderation_state = RegistrationModerationStates.PENDING.db_name
        registration.save()
        resp = app.get(registration_log_url, expect_errors=True)
        assert resp.status_code == 401

        resp = app.get(registration_log_url, auth=moderator_wrong_provider.auth, expect_errors=True)
        assert resp.status_code == 403

        resp = app.get(registration_log_url, auth=moderator.auth)
        assert resp.status_code == 200

    @pytest.mark.enable_quickfiles_creation
    def test_registries_moderation_post_accept(self, app, registration, moderator, registration_actions_url, actions_payload_base, reg_creator):
        registration.require_approval(user=registration.creator)
        registration.registration_approval.accept()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.PENDING.db_name

        actions_payload_base['data']['attributes']['trigger'] = RegistrationModerationTriggers.ACCEPT_SUBMISSION.db_name
        actions_payload_base['data']['attributes']['comment'] = 'Best registration Ive ever seen'
        actions_payload_base['data']['relationships']['target']['data']['id'] = registration._id

        resp = app.post_json_api(registration_actions_url, actions_payload_base, auth=moderator.auth)
        assert resp.status_code == 201
        assert resp.json['data']['attributes']['trigger'] == RegistrationModerationTriggers.ACCEPT_SUBMISSION.db_name
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.ACCEPTED.db_name

    @pytest.mark.enable_quickfiles_creation
    def test_registries_moderation_post_reject_moderator(self, app, registration, reg_creator, moderator, registration_actions_url, actions_payload_base):
        registration.require_approval(user=registration.creator)
        registration.registration_approval.accept()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.PENDING.db_name

        actions_payload_base['data']['attributes']['trigger'] = RegistrationModerationTriggers.REJECT_SUBMISSION.db_name
        actions_payload_base['data']['attributes']['comment'] = 'Worst registration Ive ever seen'
        actions_payload_base['data']['relationships']['target']['data']['id'] = registration._id

        resp = app.post_json_api(registration_actions_url, actions_payload_base, auth=moderator.auth)
        assert resp.status_code == 201
        assert resp.json['data']['attributes']['trigger'] == RegistrationModerationTriggers.REJECT_SUBMISSION.db_name
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.REJECTED.db_name

    @pytest.mark.enable_quickfiles_creation
    def test_registries_moderation_post_embargo(self, app, embargo_registration, moderator, provider, embargo_registration_actions_url, actions_payload_base, reg_creator):
        assert embargo_registration.moderation_state == RegistrationModerationStates.INITIAL.db_name
        embargo_registration.sanction.accept()
        embargo_registration.refresh_from_db()
        assert embargo_registration.moderation_state == RegistrationModerationStates.PENDING.db_name

        actions_payload_base['data']['attributes']['trigger'] = RegistrationModerationTriggers.ACCEPT_SUBMISSION.db_name
        actions_payload_base['data']['attributes']['comment'] = 'Looks good! (Embargo)'
        actions_payload_base['data']['relationships']['target']['data']['id'] = embargo_registration._id

        resp = app.post_json_api(embargo_registration_actions_url, actions_payload_base, auth=moderator.auth)
        assert resp.status_code == 201
        assert resp.json['data']['attributes']['trigger'] == RegistrationModerationTriggers.ACCEPT_SUBMISSION.db_name
        embargo_registration.refresh_from_db()
        assert embargo_registration.moderation_state == RegistrationModerationStates.EMBARGO.db_name

    @pytest.mark.enable_quickfiles_creation
    def test_registries_moderation_post_embargo_reject(self, app, embargo_registration, moderator, provider, embargo_registration_actions_url, actions_payload_base, reg_creator):
        assert embargo_registration.moderation_state == RegistrationModerationStates.INITIAL.db_name
        embargo_registration.sanction.accept()
        embargo_registration.refresh_from_db()
        assert embargo_registration.moderation_state == RegistrationModerationStates.PENDING.db_name

        actions_payload_base['data']['attributes']['trigger'] = RegistrationModerationTriggers.REJECT_SUBMISSION.db_name
        actions_payload_base['data']['attributes']['comment'] = 'Looks good! (Embargo)'
        actions_payload_base['data']['relationships']['target']['data']['id'] = embargo_registration._id

        resp = app.post_json_api(embargo_registration_actions_url, actions_payload_base, auth=moderator.auth)
        assert resp.status_code == 201
        assert resp.json['data']['attributes']['trigger'] == RegistrationModerationTriggers.REJECT_SUBMISSION.db_name
        embargo_registration.refresh_from_db()
        assert embargo_registration.moderation_state == RegistrationModerationStates.REJECTED.db_name

    @pytest.mark.enable_quickfiles_creation
    def test_registries_moderation_post_withdraw_accept(self, app, retract_registration, moderator, retract_registration_actions_url, actions_payload_base, provider):
        retract_registration.sanction.accept()
        retract_registration.refresh_from_db()
        assert retract_registration.moderation_state == RegistrationModerationStates.PENDING_WITHDRAW.db_name

        actions_payload_base['data']['attributes']['trigger'] = RegistrationModerationTriggers.ACCEPT_WITHDRAWAL.db_name
        actions_payload_base['data']['attributes']['comment'] = 'Bye bye'
        actions_payload_base['data']['relationships']['target']['data']['id'] = retract_registration._id

        resp = app.post_json_api(retract_registration_actions_url, actions_payload_base, auth=moderator.auth)
        assert resp.status_code == 201
        assert resp.json['data']['attributes']['trigger'] == RegistrationModerationTriggers.ACCEPT_WITHDRAWAL.db_name
        retract_registration.refresh_from_db()
        assert retract_registration.moderation_state == RegistrationModerationStates.WITHDRAWN.db_name

    @pytest.mark.enable_quickfiles_creation
    def test_registries_moderation_post_withdraw_reject(self, app, retract_registration, moderator, retract_registration_actions_url, actions_payload_base, provider):
        retract_registration.sanction.accept()
        retract_registration.refresh_from_db()
        assert retract_registration.moderation_state == RegistrationModerationStates.PENDING_WITHDRAW.db_name

        actions_payload_base['data']['attributes']['trigger'] = RegistrationModerationTriggers.REJECT_WITHDRAWAL.db_name
        actions_payload_base['data']['attributes']['comment'] = 'Bye bye'
        actions_payload_base['data']['relationships']['target']['data']['id'] = retract_registration._id

        resp = app.post_json_api(retract_registration_actions_url, actions_payload_base, auth=moderator.auth)
        assert resp.status_code == 201
        assert resp.json['data']['attributes']['trigger'] == RegistrationModerationTriggers.REJECT_WITHDRAWAL.db_name
        retract_registration.refresh_from_db()
        assert retract_registration.moderation_state == RegistrationModerationStates.ACCEPTED.db_name

    @pytest.mark.enable_quickfiles_creation
    def test_registries_moderation_post_force_withdraw(self, app, registration, moderator, registration_actions_url, actions_payload_base, provider, reg_creator):
        registration.require_approval(user=registration.creator)
        registration.registration_approval.accept()
        registration.registration_approval.accept(user=moderator)  # Gotta make it Accepted
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.ACCEPTED.db_name

        actions_payload_base['data']['attributes']['trigger'] = RegistrationModerationTriggers.FORCE_WITHDRAW.db_name
        actions_payload_base['data']['attributes']['comment'] = 'Bye bye'
        actions_payload_base['data']['relationships']['target']['data']['id'] = registration._id

        resp = app.post_json_api(registration_actions_url, actions_payload_base, auth=moderator.auth)
        assert resp.status_code == 201
        assert resp.json['data']['attributes']['trigger'] == RegistrationModerationTriggers.FORCE_WITHDRAW.db_name
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.WITHDRAWN.db_name

    @pytest.mark.enable_quickfiles_creation
    def test_registries_moderation_post_accept_errors(self, app, registration, moderator, registration_actions_url, actions_payload_base, reg_creator):
        registration.require_approval(user=registration.creator)

        #Moderator can't submit

        actions_payload_base['data']['attributes']['trigger'] = RegistrationModerationTriggers.ACCEPT_SUBMISSION.db_name
        actions_payload_base['data']['attributes']['comment'] = 'Submitting registration'
        actions_payload_base['data']['relationships']['target']['data']['id'] = registration._id

        resp = app.post_json_api(registration_actions_url, actions_payload_base, auth=moderator.auth, expect_errors=True)
        assert resp.status_code == 403
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.INITIAL.db_name

        registration.registration_approval.accept()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.PENDING.db_name

        #Admin contributor can't approve

        actions_payload_base['data']['attributes']['trigger'] = RegistrationModerationTriggers.ACCEPT_SUBMISSION.db_name
        actions_payload_base['data']['attributes']['comment'] = 'Best registration Ive ever seen'
        actions_payload_base['data']['relationships']['target']['data']['id'] = registration._id

        resp = app.post_json_api(registration_actions_url, actions_payload_base, auth=reg_creator.auth, expect_errors=True)
        assert resp.status_code == 403
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.PENDING.db_name

    @pytest.mark.enable_quickfiles_creation
    def test_registries_moderation_post_withdraw_admin_cant_accept(self, app, retract_registration, reg_creator, retract_registration_actions_url, actions_payload_base, provider):
        retract_registration.sanction.accept()

        actions_payload_base['data']['attributes']['trigger'] = RegistrationModerationTriggers.ACCEPT_WITHDRAWAL.db_name
        actions_payload_base['data']['attributes']['comment'] = 'Bye bye'
        actions_payload_base['data']['relationships']['target']['data']['id'] = retract_registration._id

        resp = app.post_json_api(retract_registration_actions_url, actions_payload_base, auth=reg_creator.auth, expect_errors=True)
        assert resp.status_code == 403

    @pytest.mark.enable_quickfiles_creation
    def test_registries_moderation_post_embargo_admin_cant_accept(self, app, embargo_registration, provider, embargo_registration_actions_url, actions_payload_base, reg_creator):
        embargo_registration.require_approval(user=embargo_registration.creator)
        embargo_registration.registration_approval.accept()
        embargo_registration.refresh_from_db()
        assert embargo_registration.moderation_state == RegistrationModerationStates.INITIAL.db_name

        actions_payload_base['data']['attributes']['trigger'] = RegistrationModerationTriggers.ACCEPT_SUBMISSION.db_name
        actions_payload_base['data']['attributes']['comment'] = 'Looks good! (Embargo)'
        actions_payload_base['data']['relationships']['target']['data']['id'] = embargo_registration._id

        resp = app.post_json_api(embargo_registration_actions_url, actions_payload_base, auth=reg_creator.auth, expect_errors=True)
        assert resp.status_code == 403

    @pytest.mark.enable_quickfiles_creation
    def test_registries_moderation_post_admin_cant_force_withdraw(self, app, registration, moderator, registration_actions_url, actions_payload_base, provider, reg_creator):
        registration.require_approval(user=registration.creator)

        registration.registration_approval.accept()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.PENDING.db_name

        actions_payload_base['data']['attributes']['trigger'] = RegistrationModerationTriggers.ACCEPT_SUBMISSION.db_name
        actions_payload_base['data']['attributes']['comment'] = 'Best registration Ive ever seen'
        actions_payload_base['data']['relationships']['target']['data']['id'] = registration._id

        resp = app.post_json_api(registration_actions_url, actions_payload_base, auth=moderator.auth)
        assert resp.status_code == 201
        assert resp.json['data']['attributes']['trigger'] == RegistrationModerationTriggers.ACCEPT_SUBMISSION.db_name

        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.ACCEPTED.db_name

        actions_payload_base['data']['attributes']['trigger'] = RegistrationModerationTriggers.FORCE_WITHDRAW.db_name
        actions_payload_base['data']['attributes']['comment'] = 'Bye bye'
        actions_payload_base['data']['relationships']['target']['data']['id'] = registration._id

        resp = app.post_json_api(registration_actions_url, actions_payload_base, auth=reg_creator.auth, expect_errors=True)
        assert resp.status_code == 403

    @pytest.mark.parametrize(
        'moderator_trigger',
        [
            RegistrationModerationTriggers.ACCEPT_SUBMISSION,
            RegistrationModerationTriggers.REJECT_SUBMISSION
        ]
    )
    @pytest.mark.enable_quickfiles_creation
    def test_post_submission_action_persists_comment(self, app, registration, moderator, registration_actions_url, actions_payload_base, moderator_trigger):
        assert registration.actions.count() == 0
        registration.require_approval(user=registration.creator)
        registration.registration_approval.accept()

        moderator_comment = 'inane comment'
        actions_payload_base['data']['attributes']['trigger'] = moderator_trigger.db_name
        actions_payload_base['data']['attributes']['comment'] = moderator_comment
        actions_payload_base['data']['relationships']['target']['data']['id'] = registration._id
        resp = app.post_json_api(registration_actions_url, actions_payload_base, auth=moderator.auth)
        assert resp.json['data']['attributes']['comment'] == moderator_comment

        persisted_action = registration.actions.get(trigger=moderator_trigger.db_name)
        assert persisted_action.comment == moderator_comment

    @pytest.mark.parametrize(
        'moderator_trigger',
        [
            RegistrationModerationTriggers.ACCEPT_WITHDRAWAL,
            RegistrationModerationTriggers.REJECT_WITHDRAWAL,
        ]
    )
    @pytest.mark.enable_quickfiles_creation
    def test_post_withdrawal_action_persists_comment(self, app, registration, moderator, registration_actions_url, actions_payload_base, moderator_trigger):
        assert registration.actions.count() == 0
        registration.is_public = True
        registration.retract_registration(user=registration.creator)
        registration.retraction.accept()

        moderator_comment = 'inane comment'
        actions_payload_base['data']['attributes']['trigger'] = moderator_trigger.db_name
        actions_payload_base['data']['attributes']['comment'] = moderator_comment
        actions_payload_base['data']['relationships']['target']['data']['id'] = registration._id
        resp = app.post_json_api(registration_actions_url, actions_payload_base, auth=moderator.auth)
        assert resp.json['data']['attributes']['comment'] == moderator_comment

        persisted_action = registration.actions.get(trigger=moderator_trigger.db_name)
        assert persisted_action.comment == moderator_comment

    @pytest.mark.enable_quickfiles_creation
    def test_post_force_withdraw_action_persists_comment(self, app, registration, moderator, registration_actions_url, actions_payload_base):
        assert registration.actions.count() == 0
        registration.is_public = True
        registration.update_moderation_state()  # implicit ACCEPTED state from RegistrationFactory

        moderator_comment = 'inane comment'
        force_withdraw_trigger = RegistrationModerationTriggers.FORCE_WITHDRAW.db_name
        actions_payload_base['data']['attributes']['trigger'] = force_withdraw_trigger
        actions_payload_base['data']['attributes']['comment'] = moderator_comment
        actions_payload_base['data']['relationships']['target']['data']['id'] = registration._id
        resp = app.post_json_api(registration_actions_url, actions_payload_base, auth=moderator.auth)

        expected_comment = 'Force withdrawn by moderator: ' + moderator_comment
        assert resp.json['data']['attributes']['comment'] == expected_comment
        persisted_action = registration.actions.get(trigger=force_withdraw_trigger)
        assert persisted_action.comment == expected_comment
