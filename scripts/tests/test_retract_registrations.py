# -*- coding: utf-8 -*-

from datetime import timedelta

from django.utils import timezone
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from osf.models import NodeLog
from osf_tests.factories import RegistrationFactory, UserFactory

from scripts.retract_registrations import main


class TestRetractRegistrations(OsfTestCase):

    def setUp(self):
        super(TestRetractRegistrations, self).setUp()
        self.user = UserFactory()
        self.registration = RegistrationFactory(creator=self.user)
        self.registration.is_public = True
        self.registration.retract_registration(self.user)
        self.registration.save()

    def test_new_retraction_should_not_be_retracted(self):
        assert_false(self.registration.is_retracted)

        main(dry_run=False)
        assert_false(self.registration.is_retracted)

    def test_should_not_retract_pending_retraction_less_than_48_hours_old(self):
        # Retraction#iniation_date is read only
        self.registration.retraction.initiation_date = (timezone.now() - timedelta(hours=47))
        self.registration.retraction.save()
        assert_false(self.registration.is_retracted)

        main(dry_run=False)
        assert_false(self.registration.is_retracted)

    def test_should_retract_pending_retraction_that_is_48_hours_old(self):
        # Retraction#iniation_date is read only
        self.registration.retraction.initiation_date = (timezone.now() - timedelta(hours=48))
        self.registration.retraction.save()
        assert_false(self.registration.is_retracted)

        main(dry_run=False)
        self.registration.retraction.refresh_from_db()
        assert_true(self.registration.is_retracted)

    def test_should_retract_pending_retraction_more_than_48_hours_old(self):
        # Retraction#iniation_date is read only
        self.registration.retraction.initiation_date = (timezone.now() - timedelta(days=365))
        self.registration.retraction.save()
        assert_false(self.registration.is_retracted)

        main(dry_run=False)
        self.registration.retraction.refresh_from_db()
        assert_true(self.registration.is_retracted)

    def test_retraction_adds_to_parent_projects_log(self):
        initial_project_logs = len(self.registration.registered_from.logs.all())
        # Retraction#iniation_date is read only
        self.registration.retraction.initiation_date =(timezone.now() - timedelta(days=365))
        self.registration.retraction.save()
        assert_false(self.registration.is_retracted)

        main(dry_run=False)
        self.registration.retraction.refresh_from_db()
        assert_true(self.registration.is_retracted)
        # Logs: Created, made public, retraction initiated, retracted approved
        assert_equal(len(self.registration.registered_from.logs.all()), initial_project_logs + 1)
