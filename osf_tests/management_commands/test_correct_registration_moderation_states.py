import mock

from django.utils import timezone
from osf.management.commands.correct_registration_moderation_states import correct_registration_moderation_states
from osf.models import Registration
from osf.utils.workflows import RegistrationModerationStates, SanctionStates
from osf_tests.factories import (
    EmbargoFactory,
    EmbargoTerminationApprovalFactory,
    RegistrationApprovalFactory,
    RegistrationProviderFactory,
    RetractionFactory,
)
from tests.base import OsfTestCase


class TestCorrectRegistrationModerationState(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.embargo = EmbargoFactory()
        self.registration_approval = RegistrationApprovalFactory()
        self.retraction = RetractionFactory()
        self.embargo_termination = EmbargoTerminationApprovalFactory()
        self.provider = RegistrationProviderFactory()

        for sanction in [self.embargo, self.registration_approval, self.retraction, self.embargo_termination]:
            registration = sanction.target_registration
            registration.provider = self.provider
            registration.save()

        # EmbargoTerminationFactory actually calls terminate_embargo,
        # which updates state in the new world
        self.embargo_termination.target_registration.moderation_state = RegistrationModerationStates.INITIAL.db_name
        self.embargo_termination.target_registration.save()

    def test_correct_registration_moderation_states(self):
        self.embargo.approval_stage = SanctionStates.MODERATOR_REJECTED
        self.embargo.save()
        self.registration_approval.approval_stage = SanctionStates.APPROVED
        self.registration_approval.save()
        self.retraction.approval_stage = SanctionStates.PENDING_MODERATION
        self.retraction.save()
        self.embargo_termination.approval_stage = SanctionStates.REJECTED
        self.embargo_termination.save()

        empty_state_counts = {state.db_name: 0 for state in RegistrationModerationStates}
        expected_initial_states = dict(empty_state_counts)
        expected_initial_states.update({'initial': 4})
        assert self.provider.get_reviewable_state_counts() == expected_initial_states

        corrected_count = correct_registration_moderation_states()
        assert corrected_count == 4

        expected_end_states = dict(empty_state_counts)
        expected_end_states.update(
            {'accepted': 1, 'rejected': 1, 'pending_withdraw': 1, 'embargo': 1}
        )
        assert self.provider.get_reviewable_state_counts() == expected_end_states

    def test_correct_registration_moderation_states_only_collects_initial_registrations(self):
        # Implicitly invoke update_moderation_state.
        # We should not attempt to update state on these Registrations.
        # Also should not attempt to update self.registration_approval, which should be in initial
        self.embargo.to_COMPLETED()
        self.retraction.to_APPROVED()

        with mock.patch.object(Registration, 'update_moderation_state') as mock_update:
            correct_registration_moderation_states()

        assert mock_update.call_count == 1

    def test_correct_registration_moderation_states_ignores_deleted_registrations(self):
        deleted_registration = self.registration_approval.target_registration
        deleted_registration.deleted = timezone.now()
        deleted_registration.save()

        with mock.patch.object(Registration, 'update_moderation_state') as mock_update:
            correct_registration_moderation_states()

        # Shouldn't attempt to update self.registration_approval (deleted)
        # or self.embargo (correctly in 'initial')
        assert mock_update.call_count == 2

    def test_correct_registration_moderation_states_only_reports_updated_registrations(self):
        # INITIAL is the correct state for a Registration with an
        # Embargo or a RegistrationApproval in UNAPPROVED state
        corrected_count = correct_registration_moderation_states()
        assert corrected_count == 2
