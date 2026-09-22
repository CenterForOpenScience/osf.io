from datetime import timedelta
from unittest import mock
import pytest
from django.utils import timezone

from tests.base import OsfTestCase
from osf.models import Embargo, NodeLog, Registration, SpamStatus
from osf_tests.factories import RegistrationFactory, UserFactory

from scripts.embargo_registrations import main


class TestRetractRegistrations(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.registration = RegistrationFactory(creator=self.user)
        self.registration.embargo_registration(
            self.user,
            timezone.now() + timedelta(days=10)
        )
        self.registration.save()

    def test_new_embargo_should_be_unapproved(self):
        assert self.registration.is_pending_embargo
        assert not self.registration.embargo_end_date

        main(dry_run=False)
        assert self.registration.is_pending_embargo
        assert not self.registration.embargo_end_date

    def test_should_not_activate_pending_embargo_less_than_48_hours_old(self):
        self.registration.embargo.initiation_date = timezone.now() - timedelta(hours=47)
        self.registration.embargo.save()
        assert not self.registration.embargo_end_date

        main(dry_run=False)
        self.registration.embargo.refresh_from_db()
        self.registration.refresh_from_db()
        assert self.registration.is_pending_embargo
        assert not self.registration.embargo_end_date

    def test_should_activate_pending_embargo_that_is_48_hours_old(self):
        self.registration.embargo.initiation_date = timezone.now() - timedelta(hours=48)
        self.registration.embargo.save()
        assert self.registration.is_pending_embargo
        assert not self.registration.embargo_end_date

        main(dry_run=False)
        self.registration.embargo.refresh_from_db()
        self.registration.refresh_from_db()
        assert self.registration.is_embargoed
        assert self.registration.embargo_end_date

    def test_should_activate_pending_embargo_more_than_48_hours_old(self):
        self.registration.embargo.initiation_date = timezone.now() - timedelta(days=365)
        self.registration.embargo.save()
        assert self.registration.is_pending_embargo
        assert not self.registration.embargo_end_date

        main(dry_run=False)
        self.registration.embargo.refresh_from_db()
        self.registration.refresh_from_db()
        assert self.registration.is_embargoed
        assert not self.registration.is_pending_embargo
        assert self.registration.embargo_end_date

    @pytest.mark.usefixtures('mock_gravy_valet_get_verified_links')
    def test_embargo_past_end_date_should_be_completed(self):
        self.registration.embargo.accept()
        assert self.registration.embargo_end_date
        assert not self.registration.is_pending_embargo

        self.registration.embargo.end_date = timezone.now() - timedelta(days=1)
        self.registration.embargo.save()

        assert not self.registration.is_public
        main(dry_run=False)
        self.registration.embargo.refresh_from_db()
        self.registration.refresh_from_db()
        assert self.registration.is_public
        assert not self.registration.embargo_end_date
        assert not self.registration.is_pending_embargo
        assert self.registration.embargo.state == 'completed'

    def test_embargo_before_end_date_should_not_be_completed(self):
        self.registration.embargo.accept()
        assert self.registration.embargo_end_date
        assert not self.registration.is_pending_embargo

        self.registration.embargo.end_date = timezone.now() + timedelta(days=1)
        self.registration.embargo.save()

        assert not self.registration.is_public
        main(dry_run=False)
        self.registration.embargo.refresh_from_db()
        assert not self.registration.is_public
        assert self.registration.embargo_end_date
        assert not self.registration.is_pending_embargo

    def test_embargo_approval_adds_to_parent_projects_log(self):
        assert not self.registration.registered_from.logs.filter(
                action=NodeLog.EMBARGO_APPROVED
            ).exists()

        self.registration.embargo.initiation_date = timezone.now() - timedelta(days=365)
        self.registration.embargo.save()
        main(dry_run=False)

        assert self.registration.registered_from.logs.filter(
                action=NodeLog.EMBARGO_APPROVED
            ).exists()

    @pytest.mark.usefixtures('mock_gravy_valet_get_verified_links')
    def test_embargo_completion_adds_to_parent_projects_log(self):
        assert not self.registration.registered_from.logs.filter(
                action=NodeLog.EMBARGO_COMPLETED
            ).exists()

        self.registration.embargo.accept()
        self.registration.embargo.end_date = timezone.now() - timedelta(days=1)
        self.registration.embargo.save()

        main(dry_run=False)
        assert self.registration.registered_from.logs.filter(
                action=NodeLog.EMBARGO_COMPLETED
            ).exists()

    @pytest.mark.usefixtures('mock_gravy_valet_get_verified_links')
    def test_failed_completion_rolls_back_embargo_state(self):

        self.registration.embargo.accept()
        self.registration.embargo.end_date = timezone.now() - timedelta(days=1)
        self.registration.embargo.save()
        self.registration.spam_status = SpamStatus.SPAM
        self.registration.save()

        main(dry_run=False)

        self.registration.embargo.refresh_from_db()
        self.registration.refresh_from_db()
        assert not self.registration.is_public
        assert self.registration.embargo.state == Embargo.APPROVED
        assert not Embargo.objects.stuck_completed().filter(id=self.registration.embargo.id).exists()

        self.registration.spam_status = SpamStatus.HAM
        self.registration.save()
        main(dry_run=False)
        self.registration.refresh_from_db()
        assert self.registration.is_public

    @pytest.mark.usefixtures('mock_gravy_valet_get_verified_links')
    def test_orphaned_active_embargo_does_not_abort_run(self):
        other_user = UserFactory()
        other_registration = RegistrationFactory(creator=other_user)
        other_registration.embargo_registration(
            other_user,
            timezone.now() + timedelta(days=10)
        )
        other_registration.save()
        other_registration.embargo.accept()
        other_registration.embargo.end_date = timezone.now() - timedelta(days=1)
        other_registration.embargo.save()

        self.registration.embargo.accept()
        self.registration.embargo.end_date = timezone.now() - timedelta(days=1)
        self.registration.embargo.save()
        broken_embargo_id = self.registration.embargo.id

        real_get = Registration.objects.get

        def get_with_simulated_race(*args, **kwargs):
            embargo_kwarg = kwargs.get('embargo')
            if embargo_kwarg is not None and embargo_kwarg.id == broken_embargo_id:
                raise Registration.DoesNotExist()
            return real_get(*args, **kwargs)

        with mock.patch.object(Registration.objects, 'get', side_effect=get_with_simulated_race):
            main(dry_run=False)

        other_registration.refresh_from_db()
        assert other_registration.is_public
        self.registration.refresh_from_db()
        assert not self.registration.is_public
