# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import RegistrationFactory
from tests.factories import UserFactory

from scripts.embargo_registrations import main


class TestRetractRegistrations(OsfTestCase):

    def setUp(self):
        super(TestRetractRegistrations, self).setUp()
        self.user = UserFactory()
        self.registration = RegistrationFactory(creator=self.user)
        self.registration.is_public = True
        self.registration.embargo_registration(
            self.user,
            date.today() + timedelta(days=10)
        )
        self.registration.save()

    def test_new_embargo_should_be_unapproved(self):
        assert_true(self.registration.pending_embargo)
        assert_false(self.registration.is_embargoed)

        main(dry_run=False)
        assert_true(self.registration.pending_embargo)
        assert_false(self.registration.is_embargoed)

    def test_should_not_activate_pending_embargo_less_than_48_hours_old(self):
        # Embargo#iniation_date is read only
        self.registration.embargo._fields['initiation_date'].__set__(
            self.registration.embargo,
            (datetime.utcnow() - timedelta(hours=47)),
            safe=True
        )
        self.registration.embargo.save()
        assert_false(self.registration.is_embargoed)

        main(dry_run=False)
        assert_false(self.registration.is_embargoed)

    def test_should_activate_pending_embargo_that_is_48_hours_old(self):
        # Embargo#iniation_date is read only
        self.registration.embargo._fields['initiation_date'].__set__(
            self.registration.embargo,
            (datetime.utcnow() - timedelta(hours=48)),
            safe=True
        )
        self.registration.embargo.save()
        assert_true(self.registration.pending_embargo)
        assert_false(self.registration.is_embargoed)

        main(dry_run=False)
        assert_false(self.registration.pending_embargo)
        assert_true(self.registration.is_embargoed)

    def test_should_activate_pending_embargo_more_than_48_hours_old(self):
        # Embargo#iniation_date is read only
        self.registration.embargo._fields['initiation_date'].__set__(
            self.registration.embargo,
            (datetime.utcnow() - timedelta(days=365)),
            safe=True
        )
        self.registration.embargo.save()
        assert_true(self.registration.pending_embargo)
        assert_false(self.registration.is_embargoed)

        main(dry_run=False)
        assert_false(self.registration.pending_embargo)
        assert_true(self.registration.is_embargoed)
