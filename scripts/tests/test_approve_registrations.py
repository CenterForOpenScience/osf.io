from datetime import timedelta

from django.utils import timezone

from tests.base import OsfTestCase
from osf.models import NodeLog
from osf_tests.factories import RegistrationFactory, UserFactory

from scripts.approve_registrations import main


class TestApproveRegistrations(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.registration = RegistrationFactory(creator=self.user, archive=False)
        self.registration.is_public = True
        self.registration.require_approval(self.user)

    def test_new_registration_should_not_be_approved(self):
        self.assertTrue(self.registration.is_pending_registration)

        main(dry_run=False)
        self.assertFalse(self.registration.is_registration_approved)

    def test_should_not_approve_pending_registration_less_than_48_hours_old(self):
        self.registration.registration_approval.initiation_date = timezone.now() - timedelta(hours=47)
        self.registration.registration_approval.save()
        self.assertFalse(self.registration.is_registration_approved)

        main(dry_run=False)
        self.assertFalse(self.registration.is_registration_approved)

    def test_should_approve_pending_registration_that_is_48_hours_old(self):
        self.assertTrue(self.registration.registration_approval.state)  # sanity check
        self.registration.registration_approval.initiation_date = timezone.now() - timedelta(hours=48)
        self.registration.registration_approval.save()
        self.assertFalse(self.registration.is_registration_approved)

        main(dry_run=False)
        self.registration.registration_approval.reload()
        self.assertTrue(self.registration.is_registration_approved)

    def test_should_approve_pending_registration_more_than_48_hours_old(self):
        self.registration.registration_approval.initiation_date = timezone.now() - timedelta(days=365)
        self.registration.registration_approval.save()
        self.assertFalse(self.registration.is_registration_approved)

        main(dry_run=False)
        self.registration.registration_approval.reload()
        self.assertTrue(self.registration.is_registration_approved)

    def test_registration_adds_to_parent_projects_log(self):
        self.assertFalse(
            self.registration.registered_from.logs.filter(
                action=NodeLog.REGISTRATION_APPROVAL_APPROVED
            ).exists()
        )
        self.assertFalse(
            self.registration.registered_from.logs.filter(
                action=NodeLog.PROJECT_REGISTERED
            ).exists()
        )
        self.assertFalse(self.registration.is_registration_approved)

        self.registration.registration_approval.initiation_date = timezone.now() - timedelta(days=365)
        self.registration.registration_approval.save()
        main(dry_run=False)
        self.registration.registration_approval.reload()

        self.assertTrue(self.registration.is_registration_approved)
        self.assertTrue(self.registration.is_public)
        self.assertTrue(
            self.registration.registered_from.logs.filter(
                action=NodeLog.REGISTRATION_APPROVAL_APPROVED
            ).exists()
        )
        self.assertTrue(
            self.registration.registered_from.logs.filter(
                action=NodeLog.PROJECT_REGISTERED
            ).exists()
        )
