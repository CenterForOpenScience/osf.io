"""Tests related to embargoes of registrations"""

import datetime
import unittest

from nose.tools import *  #noqa
from tests.base import fake, OsfTestCase
from tests.factories import EmbargoFactory, RegistrationFactory, UserFactory

from framework.exceptions import PermissionsError
from modularodm.exceptions import ValidationValueError


class RegistrationEmbargoModelsTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationEmbargoModelsTestCase, self).setUp()
        self.user = UserFactory()
        self.registration = RegistrationFactory(creator=self.user)
        self.embargo = EmbargoFactory(user=self.user)

    def test_invalid_state_raises_ValidationValueError(self):
        with assert_raises(ValidationValueError):
            self.embargo.state = 'not a valid state'
            self.embargo.save()

    def test_embargo_from_non_admin_raises_PermissionsError(self):
        embargo_end_date = datetime.date(2099, 1, 1)
        self.registration.remove_permission(self.user, 'admin')
        self.registration.save()
        self.registration.reload()
        with assert_raises(PermissionsError):
            self.registration.embargo_registration(self.user, embargo_end_date)

    def test_embargo_end_date_in_past_raises_ValidationValueError(self):
        with assert_raises(ValidationValueError):
            self.registration.embargo_registration(
                self.user,
                datetime.date(1999, 1, 1)
            )

    def test_embargo_end_date_today_raises_ValidationValueError(self):
        with assert_raises(ValidationValueError):
            self.registration.embargo_registration(
                self.user,
                datetime.date.today()
            )

    def test_embargo_end_date_in_far_future_raises_ValidationValueError(self):
        with assert_raises(ValidationValueError):
            self.registration.embargo_registration(
                self.user,
                datetime.date(2099, 1, 1)
            )

    def test_embargo_with_valid_end_date_starts_pending_embargo(self):
        self.registration.embargo_registration(
            self.user,
            datetime.date.today() + datetime.timedelta(days=10)
        )
        self.registration.save()
        self.registration.reload()
        assert_true(self.registration.pending_embargo)
