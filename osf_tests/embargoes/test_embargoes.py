from unittest import mock
import pytest
import datetime

from osf.models import Sanction

from osf_tests.factories import (
    AuthUserFactory,
    EmbargoFactory
)

from scripts.embargo_registrations import main as approve_embargos
from django.utils import timezone
from osf.utils.workflows import RegistrationModerationStates


@pytest.mark.django_db
class TestDraftRegistrations:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration(self, user):
        end_date = timezone.now() + datetime.timedelta(days=3)  # embargo days must be 3 days in the future
        embargo = EmbargoFactory(end_date=end_date)
        embargo.state = Sanction.APPROVED
        embargo.save()
        return embargo.registrations.last()

    def test_request_early_termination_too_late(self, registration, user):
        """
        This is for an edge case test for where embargos are frozen and never expire when the user requests they be
        terminated with embargo with less then 48 hours before it would expire anyway.
        """

        registration.request_embargo_termination(user)
        mock_now = timezone.now() + datetime.timedelta(days=6)
        with mock.patch.object(timezone, 'now', return_value=mock_now):
            approve_embargos(dry_run=False)

        registration.refresh_from_db()
        registration.embargo.refresh_from_db()
        registration.embargo_termination_approval.refresh_from_db()

        assert registration.embargo_termination_approval.state == Sanction.APPROVED
        registration.update_moderation_state()
        assert registration.moderation_state == RegistrationModerationStates.ACCEPTED.db_name
