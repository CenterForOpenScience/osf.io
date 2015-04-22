"""Tests related to embargoes of registrations"""

import datetime
import unittest

from nose.tools import *  #noqa
from tests.base import fake, OsfTestCase
from tests.factories import (
    AuthUserFactory, EmbargoFactory, RegistrationFactory, UserFactory,
)

from framework.exceptions import PermissionsError
from modularodm.exceptions import ValidationValueError
from website.exceptions import (
    InvalidEmbargoDisapprovalToken, InvalidEmbargoApprovalToken, NodeStateError,
)


class RegistrationEmbargoModelsTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationEmbargoModelsTestCase, self).setUp()
        self.user = UserFactory()
        self.registration = RegistrationFactory(creator=self.user)
        self.embargo = EmbargoFactory(user=self.user)

    # Validator tests
    def test_invalid_state_raises_ValidationValueError(self):
        with assert_raises(ValidationValueError):
            self.embargo.state = 'not a valid state'
            self.embargo.save()

    # Node#embargo_registration tests
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
        assert_true(self.registration.pending_embargo)

    def test_embargo_non_registration_raises_NodeStateError(self):
        self.registration.is_registration = False
        self.registration.save()
        with assert_raises(NodeStateError):
            self.registration.embargo_registration(
                self.user,
                (datetime.date.today() + datetime.timedelta(days=10))
            )
        assert_false(self.registration.pending_embargo)

    # Embargo#approve_embargo tests
    def test_invalid_approval_token_raises_InvalidEmbargoApprovalToken(self):
        self.registration.embargo_registration(
            self.user,
            (datetime.date.today() + datetime.timedelta(days=10))
        )
        self.registration.save()
        assert_true(self.registration.pending_embargo)
        invalid_approval_token = 'not a real token'
        with assert_raises(InvalidEmbargoApprovalToken):
            self.registration.embargo.approve_embargo(self.user, invalid_approval_token)
        assert_true(self.registration.pending_embargo)
        assert_false(self.registration.is_embargoed)

    def test_non_admin_approval_token_raises_PermissionsError(self):
        non_admin = UserFactory()
        self.registration.embargo_registration(
            self.user,
            (datetime.date.today() + datetime.timedelta(days=10))
        )
        self.registration.save()
        assert_true(self.registration.pending_embargo)
        approval_token = self.registration.embargo.approval_state[self.user._id]['approval_token']
        with assert_raises(PermissionsError):
            self.registration.embargo.approve_embargo(non_admin, approval_token)
        assert_true(self.registration.pending_embargo)

    def test_one_approval_with_one_admin_embargoes(self):
        self.registration.embargo_registration(
            self.user,
            (datetime.date.today() + datetime.timedelta(days=10))
        )
        self.registration.save()
        assert_true(self.registration.pending_embargo)
        approval_token = self.registration.embargo.approval_state[self.user._id]['approval_token']
        self.registration.embargo.approve_embargo(self.user, approval_token)
        assert_true(self.registration.is_embargoed)
        assert_false(self.registration.pending_embargo)

    def test_one_approval_with_two_admins_stays_pending(self):
        admin2 = UserFactory()
        self.registration.contributors.append(admin2)
        self.registration.add_permission(admin2, 'admin', save=True)
        self.registration.embargo_registration(
            self.user,
            (datetime.date.today() + datetime.timedelta(days=10))
        )
        self.registration.save()

        # First admin approves
        approval_token = self.registration.embargo.approval_state[self.user._id]['approval_token']
        self.registration.embargo.approve_embargo(self.user, approval_token)
        assert_true(self.registration.pending_embargo)
        num_of_approvals = sum([val['has_approved'] for val in self.registration.embargo.approval_state.values()])
        assert_equal(num_of_approvals, 1)

        # Second admin approves
        approval_token = self.registration.embargo.approval_state[admin2._id]['approval_token']
        self.registration.embargo.approve_embargo(admin2, approval_token)
        assert_true(self.registration.is_embargoed)
        assert_false(self.registration.pending_embargo)
        num_of_approvals = sum([val['has_approved'] for val in self.registration.embargo.approval_state.values()])
        assert_equal(num_of_approvals, 2)

    # Embargo#disapprove_embargo tests
    def test_invalid_disapproval_token_raises_InvalidEmbargoDisapprovalToken(self):
        self.registration.embargo_registration(
            self.user,
            (datetime.date.today() + datetime.timedelta(days=10))
        )
        self.registration.save()
        assert_true(self.registration.pending_embargo)
        invalid_disapproval_token = 'not a real token'
        with assert_raises(InvalidEmbargoDisapprovalToken):
            self.registration.embargo.disapprove_embargo(self.user, invalid_disapproval_token)
        assert_true(self.registration.pending_embargo)
        assert_false(self.registration.is_embargoed)

    def test_non_admin_disapproval_token_raises_PermissionsError(self):
        non_admin = UserFactory()
        self.registration.embargo_registration(
            self.user,
            (datetime.date.today() + datetime.timedelta(days=10))
        )
        self.registration.save()
        assert_true(self.registration.pending_embargo)
        disapproval_token = self.registration.embargo.approval_state[self.user._id]['disapproval_token']
        with assert_raises(PermissionsError):
            self.registration.embargo.disapprove_embargo(non_admin, disapproval_token)
        assert_true(self.registration.pending_embargo)

    def test_one_disapproval_cancels_embargo(self):
        self.registration.embargo_registration(
            self.user,
            (datetime.date.today() + datetime.timedelta(days=10))
        )
        self.registration.save()
        assert_true(self.registration.pending_embargo)
        disapproval_token = self.registration.embargo.approval_state[self.user._id]['disapproval_token']
        self.registration.embargo.disapprove_embargo(self.user, disapproval_token)
        assert_equal(self.registration.embargo.state, 'cancelled')
        assert_false(self.registration.pending_embargo)
        assert_false(self.registration.is_embargoed)


class RegistrationEmbargoViewsTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationEmbargoViewsTestCase, self).setUp()
        self.user = AuthUserFactory()
        self.registration = RegistrationFactory(creator=self.user)

    # node_registration_embargo_approve tests
    def test_GET_from_logged_out_user_raises_401(self):
        unauthorized_user = UserFactory()
        res = self.app.get(
            self.registration.web_url_for('node_registration_embargo_approve', token='aasdflkjalsdkf'),
            auth=unauthorized_user,
            expect_errors=True
        )
        assert_equal(res.status_code, 401)

    def test_GET_approve_registration_without_embargo_raises_400(self):
        assert_false(self.registration.pending_embargo)
        res = self.app.get(
            self.registration.web_url_for('node_registration_embargo_approve', token='aasdflkjalsdkf'),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_GET_approve_with_invalid_token_returns_BAD_REQUEST(self):
        self.registration.embargo_registration(
            self.user,
            (datetime.date.today() + datetime.timedelta(days=10))
        )
        self.registration.save()
        assert_true(self.registration.pending_embargo)

        res = self.app.get(
            self.registration.web_url_for('node_registration_embargo_approve', token='invalid token'),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_GET_approve_with_wrong_token_returns_BAD_REQUEST(self):
        admin2 = UserFactory()
        self.registration.contributors.append(admin2)
        self.registration.add_permission(admin2, 'admin', save=True)
        self.registration.embargo_registration(
            self.user,
            (datetime.date.today() + datetime.timedelta(days=10))
        )
        self.registration.save()
        assert_true(self.registration.pending_embargo)
        wrong_approval_token = self.registration.embargo.approval_state[admin2._id]['approval_token']
        res = self.app.get(
            self.registration.web_url_for('node_registration_embargo_approve', token=wrong_approval_token),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_GET_approve_with_valid_token_returns_302(self):
        self.registration.embargo_registration(
            self.user,
            (datetime.date.today() + datetime.timedelta(days=10))
        )
        self.registration.save()
        assert_true(self.registration.pending_embargo)
        approval_token = self.registration.embargo.approval_state[self.user._id]['approval_token']
        res = self.app.get(
            self.registration.web_url_for('node_registration_embargo_approve', token=approval_token),
            auth=self.user.auth,
        )
        self.registration.embargo.reload()
        assert_true(self.registration.is_embargoed)
        assert_false(self.registration.pending_embargo)
        assert_equal(res.status_code, 302)

    # node_registration_embargo_disapprove tests
    def test_GET_from_logged_out_user_raises_401(self):
        unauthorized_user = UserFactory()
        res = self.app.get(
            self.registration.web_url_for('node_registration_embargo_disapprove', token='aasdflkjalsdkf'),
            auth=unauthorized_user,
            expect_errors=True
        )
        assert_equal(res.status_code, 401)

    def test_disapprove_registration_without_embargo_raises_400(self):
        assert_false(self.registration.pending_embargo)
        res = self.app.get(
            self.registration.web_url_for('node_registration_embargo_disapprove', token='aasdflkjalsdkf'),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_GET_disapprove_with_invalid_token_returns_BAD_REQUEST(self):
        self.registration.embargo_registration(
            self.user,
            (datetime.date.today() + datetime.timedelta(days=10))
        )
        self.registration.save()
        assert_true(self.registration.pending_embargo)

        res = self.app.get(
            self.registration.web_url_for('node_registration_embargo_disapprove', token='invalid token'),
            auth=self.user.auth,
            expect_errors=True
        )
        self.registration.embargo.reload()
        assert_true(self.registration.pending_embargo)
        assert_equal(res.status_code, 400)

    def test_GET_disapprove_with_wrong_token_returns_BAD_REQUEST(self):
        admin2 = UserFactory()
        self.registration.contributors.append(admin2)
        self.registration.add_permission(admin2, 'admin', save=True)
        self.registration.embargo_registration(
            self.user,
            (datetime.date.today() + datetime.timedelta(days=10))
        )
        self.registration.save()
        assert_true(self.registration.pending_embargo)
        wrong_disapproval_token = self.registration.embargo.approval_state[admin2._id]['disapproval_token']
        res = self.app.get(
            self.registration.web_url_for('node_registration_embargo_disapprove', token=wrong_disapproval_token),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_true(self.registration.pending_embargo)
        assert_equal(res.status_code, 400)

    def test_GET_disapprove_with_valid_token_returns_302(self):
        self.registration.embargo_registration(
            self.user,
            (datetime.date.today() + datetime.timedelta(days=10))
        )
        self.registration.save()
        assert_true(self.registration.pending_embargo)
        disapproval_token = self.registration.embargo.approval_state[self.user._id]['disapproval_token']
        res = self.app.get(
            self.registration.web_url_for('node_registration_embargo_disapprove', token=disapproval_token),
            auth=self.user.auth,
        )
        self.registration.embargo.reload()
        assert_false(self.registration.is_embargoed)
        assert_false(self.registration.pending_embargo)
        assert_equal(res.status_code, 302)

    # node_registration_embargo_post tests

    # node_registration_embargo_get tests
