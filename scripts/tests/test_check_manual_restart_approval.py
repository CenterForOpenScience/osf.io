from datetime import timedelta
from unittest import mock

from django.utils import timezone

from osf_tests.factories import RegistrationFactory, UserFactory
from scripts.check_manual_restart_approval import check_manual_restart_approval
from tests.base import OsfTestCase
from website import settings


class TestCheckManualRestartApproval(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.registration = RegistrationFactory(creator=self.user, archive=False)
        self.registration.require_approval(self.user)

    @mock.patch('scripts.check_manual_restart_approval.approve_past_pendings')
    def test_skips_if_approval_window_not_elapsed(self, mock_approve):
        self.registration.registration_approval.initiation_date = timezone.now() - timedelta(hours=47)
        self.registration.registration_approval.save()

        result = check_manual_restart_approval(self.registration._id)

        assert 'not ready for auto-approval' in result
        mock_approve.assert_not_called()

    @mock.patch('scripts.check_manual_restart_approval.approve_past_pendings')
    def test_approves_when_approval_window_elapsed(self, mock_approve):
        self.registration.registration_approval.initiation_date = (
            timezone.now() - settings.REGISTRATION_APPROVAL_TIME - timedelta(minutes=1)
        )
        self.registration.registration_approval.save()

        result = check_manual_restart_approval(self.registration._id)

        assert 'Processed manual restart approval check' in result
        mock_approve.assert_called_once_with([self.registration.registration_approval], dry_run=False)

    @mock.patch('scripts.check_manual_restart_approval.Registration.load', return_value=None)
    def test_returns_not_found_when_registration_missing(self, mock_load):
        result = check_manual_restart_approval('abc12')

        assert result == 'Registration abc12 not found'
        mock_load.assert_called_once_with('abc12')
