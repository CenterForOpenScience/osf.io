import pytest

from api.providers.workflows import Workflows
from framework.auth import Auth
from framework.exceptions import PermissionsError
from nose.tools import assert_raises
from osf.migrations import update_provider_auth_groups
from osf_tests.factories import (
    AuthUserFactory, EmbargoFactory, RegistrationProviderFactory,
    RegistrationFactory, RegistrationApprovalFactory, RetractionFactory
)
from osf.utils import tokens
from osf.utils.workflows import (
    RegistrationModerationStates,
    RegistrationModerationTriggers,
    SanctionStates
)
from tests.base import OsfTestCase
from transitions import MachineError

DUMMY_TOKEN = tokens.encode({
    'dummy': 'token'
})


@pytest.mark.enable_bookmark_creation
@pytest.mark.django_db
class TestUnmoderatedFlows():

    @pytest.fixture
    def registration_approval(self):
        return RegistrationApprovalFactory()

    @pytest.fixture
    def embargo(self):
        return EmbargoFactory()

    @pytest.fixture
    def retraction(self):
        return RetractionFactory()

    @pytest.mark.parametrize(
        'sanction_fixture, initial_state, end_state',
        [
            (
                registration_approval,
                RegistrationModerationStates.INITIAL,
                RegistrationModerationStates.ACCEPTED
            ),
            (
                embargo,
                RegistrationModerationStates.INITIAL,
                RegistrationModerationStates.EMBARGO
            ),
            (
                retraction,
                RegistrationModerationStates.PENDING_WITHDRAW_REQUEST,
                RegistrationModerationStates.WITHDRAWN
            ),
        ]
    )
    def test_approval_flow(self, sanction_fixture, initial_state, end_state):
        # using fixtures in parametrize returns the function
        sanction_object = sanction_fixture(self)
        registration = sanction_object.target_registration
        registration.update_moderation_state()

        assert registration.moderation_state == initial_state.db_name
        assert registration.sanction._id == sanction_object._id

        approval_token = sanction_object.token_for_user(registration.creator, 'approval')
        sanction_object.approve(user=registration.creator, token=approval_token)

        registration.refresh_from_db()
        assert registration.moderation_state == end_state.db_name

    @pytest.mark.parametrize(
        'sanction_fixture, initial_state, end_state',
        [
            (
                registration_approval,
                RegistrationModerationStates.INITIAL,
                RegistrationModerationStates.REVERTED
            ),
            (
                embargo,
                RegistrationModerationStates.INITIAL,
                RegistrationModerationStates.REVERTED
            ),
            (
                retraction,
                RegistrationModerationStates.PENDING_WITHDRAW_REQUEST,
                RegistrationModerationStates.ACCEPTED
            ),
        ]
    )
    def test_rejection_flow(self, sanction_fixture, initial_state, end_state):
        # using fixtures in parametrize returns the function
        sanction_object = sanction_fixture(self)
        registration = sanction_object.target_registration
        registration.update_moderation_state()

        assert registration.moderation_state == initial_state.db_name
        assert registration.sanction._id == sanction_object._id

        rejection_token = sanction_object.token_for_user(registration.creator, 'rejection')
        sanction_object.reject(user=registration.creator, token=rejection_token)

        registration.refresh_from_db()
        assert registration.moderation_state == end_state.db_name


    @pytest.mark.parametrize('sanction_fixture', [registration_approval, embargo, retraction])
    def test_approve_after_reject_fails(self, sanction_fixture):
        # using fixtures in parametrize returns the function
        sanction_object = sanction_fixture(self)
        sanction_object.to_REJECTED()
        registration = sanction_object.target_registration
        registration.update_moderation_state()

        rejection_token = sanction_object.token_for_user(registration.creator, 'rejection')
        sanction_object.reject(user=registration.creator, token=rejection_token)

        approval_token = sanction_object.token_for_user(registration.creator, 'approval')
        with assert_raises(MachineError):
            sanction_object.approve(user=registration.creator, token=approval_token)

    @pytest.mark.parametrize('sanction_fixture', [registration_approval, embargo, retraction])
    def test_reject_after_arpprove_fails(self, sanction_fixture):
        # using fixtures in parametrize returns the function
        sanction_object = sanction_fixture(self)
        sanction_object.to_APPROVED()
        registration = sanction_object.target_registration
        registration.update_moderation_state()

        rejection_token = sanction_object.token_for_user(registration.creator, 'rejection')
        with assert_raises(MachineError):
            sanction_object.reject(user=registration.creator, token=rejection_token)

    @pytest.mark.parametrize('sanction_fixture', [registration_approval, embargo, retraction])
    def test_approve_after_accept_is_noop(self, sanction_fixture):
        # using fixtures in parametrize returns the function
        sanction_object = sanction_fixture(self)
        sanction_object.to_APPROVED()
        registration = sanction_object.target_registration
        registration.update_moderation_state()
        registration_accepted_state = registration.moderation_state

        approval_token = sanction_object.token_for_user(registration.creator, 'approval')
        sanction_object.approve(user=registration.creator, token=approval_token)
        registration.refresh_from_db()
        assert registration.moderation_state == registration_accepted_state
        assert sanction_object.approval_stage is SanctionStates.APPROVED

    @pytest.mark.parametrize('sanction_fixture', [registration_approval, embargo, retraction])
    def test_approve_after_accept_is_noop(self, sanction_fixture):
        # using fixtures in parametrize returns the function
        sanction_object = sanction_fixture(self)
        sanction_object.to_REJECTED()
        registration = sanction_object.target_registration
        registration.update_moderation_state()
        registration_rejected_state = registration.moderation_state

        rejection_token = sanction_object.token_for_user(registration.creator, 'rejection')
        sanction_object.reject(user=registration.creator, token=rejection_token)
        registration.refresh_from_db()
        assert registration.moderation_state == registration_rejected_state
        assert sanction_object.approval_stage is SanctionStates.REJECTED

@pytest.mark.enable_bookmark_creation
@pytest.mark.django_db
class TestModeratedFlows():

    @pytest.fixture
    def moderator(self):
        return AuthUserFactory()

    @pytest.fixture
    def provider_admin(self):
        return AuthUserFactory()

    @pytest.fixture
    def provider(self, moderator, provider_admin):
        provider = RegistrationProviderFactory()
        update_provider_auth_groups()
        provider.get_group('moderator').user_set.add(moderator)
        provider.get_group('admin').user_set.add(provider_admin)
        provider.reviews_workflow = Workflows.PRE_MODERATION.value
        provider.save()
        return provider

    @pytest.fixture
    def registration_approval(self, provider):
        sanction = RegistrationApprovalFactory()
        registration = sanction.target_registration
        registration.provider = provider
        registration.update_moderation_state()
        registration.save()
        return sanction

    @pytest.fixture
    def embargo(self, provider):
        sanction = EmbargoFactory()
        registration = sanction.target_registration
        registration.provider = provider
        registration.update_moderation_state()
        registration.save()
        return sanction

    @pytest.fixture
    def retraction(self, provider):
        sanction = RetractionFactory()
        registration = sanction.target_registration
        registration.provider = provider
        registration.update_moderation_state()
        registration.save()
        return sanction

    @pytest.mark.parametrize(
        'sanction_fixture, initial_state, intermediate_state, end_state',
        [
            (
                registration_approval,
                RegistrationModerationStates.INITIAL,
                RegistrationModerationStates.PENDING,
                RegistrationModerationStates.ACCEPTED
            ),
            (
                embargo,
                RegistrationModerationStates.INITIAL,
                RegistrationModerationStates.PENDING,
                RegistrationModerationStates.EMBARGO
            ),
            (
                retraction,
                RegistrationModerationStates.PENDING_WITHDRAW_REQUEST,
                RegistrationModerationStates.PENDING_WITHDRAW,
                RegistrationModerationStates.WITHDRAWN
            ),
        ]
    )
    def test_approval_flow(
        self, sanction_fixture, initial_state, intermediate_state, end_state, provider, moderator):
        # using fixtures in parametrize returns the function
        sanction_object = sanction_fixture(self, provider)
        registration = sanction_object.target_registration

        assert registration.moderation_state == initial_state.db_name
        assert registration.sanction._id == sanction_object._id

        approval_token = sanction_object.token_for_user(registration.creator, 'approval')
        sanction_object.approve(user=registration.creator, token=approval_token)
        registration.refresh_from_db()
        assert registration.moderation_state == intermediate_state.db_name

        sanction_object.accept(user=moderator)
        registration.refresh_from_db()
        assert registration.moderation_state == end_state.db_name

    @pytest.mark.parametrize(
        'sanction_fixture, initial_state, end_state',
        [
            (
                registration_approval,
                RegistrationModerationStates.INITIAL,
                RegistrationModerationStates.REVERTED
            ),
            (
                embargo,
                RegistrationModerationStates.INITIAL,
                RegistrationModerationStates.REVERTED
            ),
            (
                retraction,
                RegistrationModerationStates.PENDING_WITHDRAW_REQUEST,
                RegistrationModerationStates.ACCEPTED
            ),
        ]
    )
    def test_admin_rejection_flow(self, sanction_fixture, initial_state, end_state, provider):
        # using fixtures in parametrize returns the function
        sanction_object = sanction_fixture(self, provider)
        registration = sanction_object.target_registration

        assert registration.moderation_state == initial_state.db_name
        assert registration.sanction._id == sanction_object._id

        rejection_token = sanction_object.token_for_user(registration.creator, 'rejection')
        sanction_object.reject(user=registration.creator, token=rejection_token)

        registration.refresh_from_db()
        assert registration.moderation_state == end_state.db_name

    @pytest.mark.parametrize(
        'sanction_fixture, initial_state, intermediate_state, end_state',
        [
            (
                registration_approval,
                RegistrationModerationStates.INITIAL,
                RegistrationModerationStates.PENDING,
                RegistrationModerationStates.REJECTED
            ),
            (
                embargo,
                RegistrationModerationStates.INITIAL,
                RegistrationModerationStates.PENDING,
                RegistrationModerationStates.REJECTED
            ),
            (
                retraction,
                RegistrationModerationStates.PENDING_WITHDRAW_REQUEST,
                RegistrationModerationStates.PENDING_WITHDRAW,
                RegistrationModerationStates.ACCEPTED
            ),
        ]
    )
    def test_moderator_rejection_flow(
        self, sanction_fixture, initial_state, intermediate_state, end_state, provider, moderator):
        # using fixtures in parametrize returns the function
        sanction_object = sanction_fixture(self, provider)
        registration = sanction_object.target_registration

        assert registration.moderation_state == initial_state.db_name
        assert registration.sanction._id == sanction_object._id

        approval_token = sanction_object.token_for_user(registration.creator, 'approval')
        sanction_object.approve(user=registration.creator, token=approval_token)
        registration.refresh_from_db()
        assert registration.moderation_state == intermediate_state.db_name

        sanction_object.reject(user=moderator)
        registration.refresh_from_db()
        assert registration.moderation_state == end_state.db_name

    @pytest.mark.parametrize('sanction_fixture', [registration_approval, embargo, retraction])
    def test_admin_cannot_give_moderator_approval(self, sanction_fixture, provider):
        # using fixtures in parametrize returns the function
        sanction_object = sanction_fixture(self, provider)
        sanction_object.to_PENDING_MODERATION()
        registration = sanction_object.target_registration

        approval_token = sanction_object.token_for_user(registration.creator, 'approval')
        sanction_object.approve(user=registration.creator, token=approval_token)
        assert sanction_object.approval_stage is SanctionStates.PENDING_MODERATION

        with assert_raises(PermissionsError):
            sanction_object.accept(user=registration.creator)

    @pytest.mark.parametrize('sanction_fixture', [registration_approval, embargo, retraction])
    def test_admin_cannot_reject_after_admin_approval_granted(self, sanction_fixture, provider):
        # using fixtures in parametrize returns the function
        sanction_object = sanction_fixture(self, provider)
        sanction_object.to_PENDING_MODERATION()
        registration = sanction_object.target_registration

        rejection_token = sanction_object.token_for_user(registration.creator, 'rejection')
        with assert_raises(PermissionsError):
            sanction_object.reject(user=registration.creator, token=rejection_token)

    @pytest.mark.parametrize('sanction_fixture', [registration_approval, embargo, retraction])
    def test_moderator_cannot_accept_before_admin_approval(
        self, sanction_fixture, provider, moderator):
        # using fixtures in parametrize returns the function
        sanction_object = sanction_fixture(self, provider)

        with assert_raises(PermissionsError):
            # Confirm PermissionError, not InvalidSanctionApprovalToken
            sanction_object.approve(user=moderator, token=DUMMY_TOKEN)

        with assert_raises(PermissionsError):
            sanction_object.accept(user=moderator)

    @pytest.mark.parametrize('sanction_fixture', [registration_approval, embargo, retraction])
    def test_moderator_cannot_reject_before_admin_approval(
        self, sanction_fixture, provider, moderator):
        # using fixtures in parametrize returns the function
        sanction_object = sanction_fixture(self, provider)

        with assert_raises(PermissionsError):
            sanction_object.reject(user=moderator)

    @pytest.mark.parametrize('sanction_fixture', [registration_approval, embargo, retraction])
    def test_admin_approve_after_accepted_is_noop(self, sanction_fixture, provider):
        # using fixtures in parametrize returns the function
        sanction_object = sanction_fixture(self, provider)
        registration = sanction_object.target_registration
        sanction_object.to_APPROVED()
        registration.refresh_from_db()
        registration_accepted_state = registration.moderation_state

        approval_token = sanction_object.token_for_user(registration.creator, 'approval')
        sanction_object.approve(user=registration.creator, token=approval_token)
        registration.refresh_from_db()
        assert sanction_object.approval_stage is SanctionStates.APPROVED
        assert registration.moderation_state == registration_accepted_state

    @pytest.mark.parametrize('sanction_fixture', [registration_approval, embargo, retraction])
    def test_admin_accept_after_accepted_is_noop(self, sanction_fixture, provider):
        # using fixtures in parametrize returns the function
        sanction_object = sanction_fixture(self, provider)
        registration = sanction_object.target_registration
        sanction_object.to_APPROVED()
        registration.refresh_from_db()
        registration_accepted_state = registration.moderation_state

        approval_token = sanction_object.token_for_user(registration.creator, 'approval')
        sanction_object.accept(user=registration.creator, token=approval_token)
        registration.refresh_from_db()
        assert sanction_object.approval_stage is SanctionStates.APPROVED
        assert registration.moderation_state == registration_accepted_state

    @pytest.mark.parametrize('sanction_fixture', [registration_approval, embargo, retraction])
    def test_moderator_accept_after_accepted_is_noop(self, sanction_fixture, provider, moderator):
        # using fixtures in parametrize returns the function
        sanction_object = sanction_fixture(self, provider)
        registration = sanction_object.target_registration
        sanction_object.to_APPROVED()
        registration.refresh_from_db()
        registration_accepted_state = registration.moderation_state

        sanction_object.accept(user=moderator)
        registration.refresh_from_db()
        assert sanction_object.approval_stage is SanctionStates.APPROVED
        assert registration.moderation_state == registration_accepted_state

    @pytest.mark.parametrize('sanction_fixture', [registration_approval, embargo, retraction])
    def test_admin_reject_after_accepted_raises_machine_error(self, sanction_fixture, provider):
        # using fixtures in parametrize returns the function
        sanction_object = sanction_fixture(self, provider)
        registration = sanction_object.target_registration
        sanction_object.to_APPROVED()
        registration.refresh_from_db()

        rejection_token = sanction_object.token_for_user(registration.creator, 'rejection')

        with assert_raises(MachineError):
            sanction_object.reject(user=registration.creator, token=rejection_token)

    @pytest.mark.parametrize('sanction_fixture', [registration_approval, embargo, retraction])
    def test_moderator_reject_after_accepted_raises_machine_error(
        self, sanction_fixture, provider, moderator):
        # using fixtures in parametrize returns the function
        sanction_object = sanction_fixture(self, provider)
        sanction_object.to_APPROVED()

        with assert_raises(MachineError):
            sanction_object.reject(user=moderator)

    @pytest.mark.parametrize('sanction_fixture', [registration_approval, embargo, retraction])
    @pytest.mark.parametrize(
        'rejection_state', [SanctionStates.REJECTED, SanctionStates.MODERATOR_REJECTED])
    def test_admin_reject_after_rejected_is_noop(self, sanction_fixture, rejection_state, provider):
        # using fixtures in parametrize returns the function
        sanction_object = sanction_fixture(self, provider)
        registration = sanction_object.target_registration
        reject_transition = getattr(sanction_object, f'to_{rejection_state.name}')
        reject_transition()
        registration.refresh_from_db()
        registration_rejected_state = registration.moderation_state

        rejection_token = sanction_object.token_for_user(registration.creator, 'rejection')
        sanction_object.reject(user=registration.creator, token=rejection_token)
        registration.refresh_from_db()
        assert sanction_object.approval_stage is rejection_state
        assert registration.moderation_state == registration_rejected_state


    @pytest.mark.parametrize('sanction_fixture', [registration_approval, embargo, retraction])
    @pytest.mark.parametrize(
        'rejection_state', [SanctionStates.REJECTED, SanctionStates.MODERATOR_REJECTED])
    def test_moderator_reject_after_rejected_is_noop(
        self, sanction_fixture, rejection_state, provider, moderator):
        # using fixtures in parametrize returns the function
        sanction_object = sanction_fixture(self, provider)
        registration = sanction_object.target_registration
        reject_transition = getattr(sanction_object, f'to_{rejection_state.name}')
        reject_transition()
        sanction_object.approval_stage = rejection_state
        registration.refresh_from_db()
        registration_rejected_state = registration.moderation_state

        sanction_object.reject(user=moderator)
        registration.refresh_from_db()
        assert sanction_object.approval_stage is rejection_state
        assert registration.moderation_state == registration_rejected_state

    @pytest.mark.parametrize('sanction_fixture', [registration_approval, embargo, retraction])
    @pytest.mark.parametrize(
        'rejection_state', [SanctionStates.REJECTED, SanctionStates.MODERATOR_REJECTED])
    def test_admin_approve_after_rejected_raises_machine_error(
        self, sanction_fixture, rejection_state, provider):
        # using fixtures in parametrize returns the function
        sanction_object = sanction_fixture(self, provider)
        sanction_object.approval_stage = rejection_state
        registration = sanction_object.target_registration

        approval_token = sanction_object.token_for_user(registration.creator, 'approval')
        with assert_raises(MachineError):
            sanction_object.approve(user=registration.creator, token=approval_token)

    @pytest.mark.parametrize('sanction_fixture', [registration_approval, embargo, retraction])
    @pytest.mark.parametrize(
        'rejection_state', [SanctionStates.REJECTED, SanctionStates.MODERATOR_REJECTED])
    def test_moderator_approve_after_rejected_raises_machine_error(
        self, sanction_fixture, rejection_state, provider, moderator):
        # using fixtures in parametrize returns the function
        sanction_object = sanction_fixture(self, provider)
        sanction_object.approval_stage = rejection_state
        registration = sanction_object.target_registration

        with assert_raises(MachineError):
            sanction_object.accept(user=moderator)


    @pytest.mark.parametrize('sanction_fixture', [registration_approval, embargo, retraction])
    def test_provider_admin_can_accept_as_moderator(
        self, sanction_fixture, provider, provider_admin):
        sanction_object = sanction_fixture(self, provider)
        sanction_object.accept()
        assert sanction_object.approval_stage is SanctionStates.PENDING_MODERATION

        sanction_object.accept(user=provider_admin)
        assert sanction_object.approval_stage is SanctionStates.APPROVED

    @pytest.mark.parametrize('sanction_fixture', [registration_approval, embargo, retraction])
    def test_provider_admin_can_reject_as_moderator(
        self, sanction_fixture, provider, provider_admin):
        sanction_object = sanction_fixture(self, provider)
        sanction_object.accept()
        assert sanction_object.approval_stage is SanctionStates.PENDING_MODERATION

        sanction_object.reject(user=provider_admin)
        assert sanction_object.approval_stage is SanctionStates.MODERATOR_REJECTED

@pytest.mark.enable_bookmark_creation
class TestEmbargoTerminationFlows(OsfTestCase):

    def setUp(self):
        super().setUp()
        embargo = EmbargoFactory()
        registration = embargo.target_registration
        moderator = AuthUserFactory()
        provider = RegistrationProviderFactory()

        embargo.to_APPROVED()
        embargo.save()
        update_provider_auth_groups()
        provider.get_group('moderator').user_set.add(moderator)
        provider.reviews_workflow = Workflows.PRE_MODERATION.value
        provider.save()
        registration.provider = provider
        registration.update_moderation_state()
        registration.save()

        self.embargo = embargo
        self.registration = registration
        self.user = self.registration.creator
        self.moderator = moderator
        self.provider = provider

    def test_embargo_termination_approved_by_admin(self):
        assert self.registration.moderation_state == RegistrationModerationStates.EMBARGO.db_name

        embargo_termination = self.registration.request_embargo_termination(self.user)
        pending_embargo_termination_state = RegistrationModerationStates.PENDING_EMBARGO_TERMINATION
        assert self.registration.moderation_state == pending_embargo_termination_state.db_name

        approval_token = embargo_termination.token_for_user(self.user, 'approval')
        embargo_termination.approve(user=self.user, token=approval_token)
        self.registration.refresh_from_db()
        assert self.registration.moderation_state == RegistrationModerationStates.ACCEPTED.db_name
        assert self.embargo.approval_stage is SanctionStates.COMPLETED

    def test_embargo_termination_rejected_by_admin(self):
        assert self.registration.moderation_state == RegistrationModerationStates.EMBARGO.db_name

        embargo_termination = self.registration.request_embargo_termination(self.user)
        assert self.registration.moderation_state == RegistrationModerationStates.PENDING_EMBARGO_TERMINATION.db_name

        rejection_token = embargo_termination.token_for_user(self.user, 'rejection')
        embargo_termination.reject(user=self.user, token=rejection_token)
        self.registration.refresh_from_db()
        assert self.registration.moderation_state == RegistrationModerationStates.EMBARGO.db_name

    def test_embargo_termination_doesnt_require_moderator_approval(self):
        embargo_termination = self.registration.request_embargo_termination(self.user)
        approval_token = embargo_termination.token_for_user(self.user, 'approval')
        embargo_termination.approve(user=self.user, token=approval_token)
        self.registration.refresh_from_db()
        assert self.registration.moderation_state == RegistrationModerationStates.ACCEPTED.db_name
        assert self.embargo.approval_stage is SanctionStates.COMPLETED

    def test_moderator_cannot_approve_embargo_termination(self):
        embargo_termination = self.registration.request_embargo_termination(self.user)
        with assert_raises(PermissionsError):
            embargo_termination.accept(user=self.moderator)

    def test_moderator_cannot_reject_embargo_termination(self):
        embargo_termination = self.registration.request_embargo_termination(self.user)
        with assert_raises(PermissionsError):
            embargo_termination.reject(user=self.moderator)

    def test_approve_after_approve_is_noop(self):
        embargo_termination = self.registration.request_embargo_termination(self.user)

        approval_token = embargo_termination.token_for_user(self.user, 'approval')
        embargo_termination.approve(user=self.user, token=approval_token)

        embargo_termination.approve(user=self.user, token=approval_token)
        assert embargo_termination.approval_stage is SanctionStates.APPROVED
        assert self.embargo.approval_stage is SanctionStates.COMPLETED
        assert self.registration.moderation_state == RegistrationModerationStates.ACCEPTED.db_name

    def test_reject_afer_reject_is_noop(self):
        embargo_termination = self.registration.request_embargo_termination(self.user)

        rejection_token = embargo_termination.token_for_user(self.user, 'rejection')
        embargo_termination.reject(user=self.user, token=rejection_token)

        embargo_termination.reject(user=self.user, token=rejection_token)
        assert embargo_termination.approval_stage is SanctionStates.REJECTED
        assert self.embargo.approval_stage is SanctionStates.APPROVED
        assert self.registration.moderation_state == RegistrationModerationStates.EMBARGO.db_name

    def test_reject_after_accept_raises_machine_error(self):
        embargo_termination = self.registration.request_embargo_termination(self.user)
        approval_token = embargo_termination.token_for_user(self.user, 'approval')
        embargo_termination.approve(user=self.user, token=approval_token)

        rejection_token = embargo_termination.token_for_user(self.user, 'rejection')
        with assert_raises(MachineError):
            embargo_termination.reject(user=self.user, token=rejection_token)

    def test_accept_after_reject_raises_machine_error(self):
        embargo_termination = self.registration.request_embargo_termination(self.user)
        rejection_token = embargo_termination.token_for_user(self.user, 'rejection')
        embargo_termination.reject(user=self.user, token=rejection_token)

        approval_token = embargo_termination.token_for_user(self.user, 'approval')
        with assert_raises(MachineError):
            embargo_termination.approve(user=self.user, token=approval_token)


@pytest.mark.enable_bookmark_creation
@pytest.mark.django_db
class TestModerationActions:

    @pytest.fixture
    def moderator(self):
        return AuthUserFactory()

    @pytest.fixture
    def provider(self, moderator):
        provider = RegistrationProviderFactory()
        update_provider_auth_groups()
        provider.get_group('moderator').user_set.add(moderator)
        provider.reviews_workflow = Workflows.PRE_MODERATION.value
        provider.save()
        return provider

    @pytest.fixture
    def registration_approval(self, provider):
        sanction = RegistrationApprovalFactory()
        registration = sanction.target_registration
        registration.provider = provider
        registration.update_moderation_state()
        registration.save()
        return sanction

    @pytest.fixture
    def embargo(self, provider):
        sanction = EmbargoFactory()
        registration = sanction.target_registration
        registration.provider = provider
        registration.update_moderation_state()
        registration.save()
        return sanction

    @pytest.fixture
    def retraction(self, provider):
        sanction = RetractionFactory(justification='bird')
        registration = sanction.target_registration
        registration.provider = provider
        registration.update_moderation_state()
        registration.save()
        return sanction

    @pytest.mark.parametrize('sanction_fixture', [registration_approval, embargo])
    def test_admin_accept_submission_writes_submit_action(self, sanction_fixture, provider):
        sanction_object = sanction_fixture(self, provider)
        registration = sanction_object.target_registration
        assert registration.actions.count() == 0

        sanction_object.accept()
        registration.refresh_from_db()
        latest_action = registration.actions.last()
        assert latest_action.trigger == RegistrationModerationTriggers.SUBMIT.db_name

    @pytest.mark.parametrize('sanction_fixture', [registration_approval, embargo])
    def test_moderator_accept_submission_writes_accept_submission_action(
        self, sanction_fixture, provider, moderator):
        sanction_object = sanction_fixture(self, provider)
        registration = sanction_object.target_registration
        assert registration.actions.count() == 0

        sanction_object.accept()
        sanction_object.accept(user=moderator)
        registration.refresh_from_db()
        latest_action = registration.actions.last()
        assert latest_action.trigger == RegistrationModerationTriggers.ACCEPT_SUBMISSION.db_name

    @pytest.mark.parametrize('sanction_fixture', [registration_approval, embargo])
    def test_moderator_reject_submission_writes_accept_submission_action(
        self, sanction_fixture, provider, moderator):
        sanction_object = sanction_fixture(self, provider)
        registration = sanction_object.target_registration
        assert registration.actions.count() == 0

        sanction_object.accept()
        sanction_object.reject(user=moderator)
        registration.refresh_from_db()
        latest_action = registration.actions.last()
        assert latest_action.trigger == RegistrationModerationTriggers.REJECT_SUBMISSION.db_name

    def test_admin_accept_retraction_writes_request_withdrawal_action(self, retraction):
        registration = retraction.target_registration
        assert registration.actions.count() == 0

        retraction.accept()
        registration.refresh_from_db()
        latest_action = registration.actions.last()
        assert latest_action.trigger == RegistrationModerationTriggers.REQUEST_WITHDRAWAL.db_name
        assert latest_action.comment == 'bird'


    def test_moderator_accept_retraction_writes_accept_withdrawal_action(
        self, retraction, moderator):
        registration = retraction.target_registration
        assert registration.actions.count() == 0

        retraction.accept()
        retraction.accept(user=moderator)
        registration.refresh_from_db()
        latest_action = registration.actions.last()
        assert latest_action.trigger == RegistrationModerationTriggers.ACCEPT_WITHDRAWAL.db_name

    def test_moderator_reject_retraction_writes_reject_withdrawal_action(
        self, retraction, moderator):
        registration = retraction.target_registration
        assert registration.actions.count() == 0

        retraction.accept()
        retraction.reject(user=moderator)
        registration.refresh_from_db()
        latest_action = registration.actions.last()
        assert latest_action.trigger == RegistrationModerationTriggers.REJECT_WITHDRAWAL.db_name

    @pytest.mark.parametrize('sanction_fixture', [registration_approval, embargo, retraction])
    def test_no_actions_written_on_unmoderated_accept(self, sanction_fixture):
        sanction_object = sanction_fixture(self, None)
        registration = sanction_object.target_registration

        sanction_object.accept()
        registration.refresh_from_db()
        assert sanction_object.approval_stage is SanctionStates.APPROVED
        assert registration.actions.count() == 0

    @pytest.mark.parametrize('sanction_fixture', [registration_approval, embargo, retraction])
    def test_no_actions_written_on_unmoderated_rejection(self, sanction_fixture, provider):
        sanction_object = sanction_fixture(self, provider)
        registration = sanction_object.target_registration

        rejection_token = sanction_object.token_for_user(registration.creator, 'rejection')
        sanction_object.reject(user=registration.creator, token=rejection_token)
        registration.refresh_from_db()
        assert sanction_object.approval_stage is SanctionStates.REJECTED
        assert registration.actions.count() == 0
