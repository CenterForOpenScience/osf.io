"""Tests related to retraction of public registrations"""

import datetime
from nose.tools import *  # noqa
from tests.base import fake, OsfTestCase
from tests.factories import ProjectFactory, RegistrationFactory, UserFactory, AuthUserFactory

from modularodm.exceptions import ValidationValueError
from website.exceptions import NodeStateError

from framework.auth.core import Auth


class RegistrationRetractionModelsTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationRetractionModelsTestCase, self).setUp()
        self.user = UserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)
        self.registration = RegistrationFactory(project=self.project)
        self.valid_justification = fake.sentence()
        self.invalid_justification = fake.text(max_nb_chars=3000)

    def test_invalid_state_raises_ValidationValueError(self):
        self.registration.is_public = True
        self.registration.retract_registration(self.user)
        with assert_raises(ValidationValueError):
            self.registration.retraction.state = 'invalid_state'
            self.registration.retraction.save()

    def test_one_disapproval_cancels_retraction(self):
        self.registration.is_public = True
        self.registration.retract_registration(self.user)
        self.registration.save()

        self.registration.reload()
        disapproval_token = self.registration.retraction.approval_state[self.user._id]['disapproval_token']
        assert_equal(self.registration.retraction.state, 'pending')
        self.registration.retraction.disapprove_retraction(self.user, disapproval_token)
        assert_equal(self.registration.retraction.state, 'cancelled')

    def test_one_approval_with_one_admin_retracts(self):
        self.registration.is_public = True
        self.registration.retract_registration(self.user)
        self.registration.save()

        self.registration.reload()
        approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        assert_equal(self.registration.retraction.state, 'pending')
        self.registration.retraction.approve_retraction(self.user, approval_token)
        assert_true(self.registration.retraction.is_retracted)
        num_of_approvals = sum([val['has_approved'] for val in self.registration.retraction.approval_state.values()])
        assert_equal(num_of_approvals, 1)

    def test_retraction_of_registration_pending_embargo_cancels_embargo(self):
        self.registration.is_public = True
        self.registration.embargo_registration(
            self.user,
            (datetime.date.today() + datetime.timedelta(days=10)),
            for_existing_registration=True
        )
        self.registration.save()
        assert_true(self.registration.pending_embargo)

        self.registration.retract_registration(self.user)
        self.registration.save()
        assert_true(self.registration.pending_retraction)

        approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        self.registration.retraction.approve_retraction(self.user, approval_token)
        assert_false(self.registration.pending_retraction)
        assert_true(self.registration.is_retracted)
        assert_false(self.registration.pending_embargo)
        assert_false(self.registration.is_embargoed)
        assert_equal(self.registration.embargo.state, 'cancelled')

    def test_retraction_of_registration_in_active_embargo_cancels_embargo(self):
        self.registration.is_public = True
        self.registration.embargo_registration(
            self.user,
            (datetime.date.today() + datetime.timedelta(days=10)),
            for_existing_registration=True
        )
        self.registration.save()
        assert_true(self.registration.pending_embargo)

        embargo_approval_token = self.registration.embargo.approval_state[self.user._id]['approval_token']
        self.registration.embargo.approve_embargo(self.user, embargo_approval_token)
        assert_false(self.registration.pending_embargo)
        assert_true(self.registration.is_embargoed)

        self.registration.retract_registration(self.user)
        self.registration.save()
        assert_true(self.registration.pending_retraction)

        retraction_approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        self.registration.retraction.approve_retraction(self.user, retraction_approval_token)
        assert_false(self.registration.pending_retraction)
        assert_true(self.registration.is_retracted)
        assert_false(self.registration.pending_embargo)
        assert_false(self.registration.is_embargoed)
        assert_equal(self.registration.embargo.state, 'cancelled')

    def test_two_approvals_with_two_admins_retracts(self):
        self.admin2 = UserFactory()
        self.registration.contributors.append(self.admin2)
        self.registration.add_permission(self.admin2, 'admin', save=True)
        self.registration.is_public = True
        self.registration.retract_registration(self.user)
        self.registration.save()

        self.registration.reload()
        # First admin approves
        approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        self.registration.retraction.approve_retraction(self.user, approval_token)
        assert_equal(self.registration.retraction.state, 'pending')
        num_of_approvals = sum([val['has_approved'] for val in self.registration.retraction.approval_state.values()])
        assert_equal(num_of_approvals, 1)

        # Second admin approves
        approval_token = self.registration.retraction.approval_state[self.admin2._id]['approval_token']
        self.registration.retraction.approve_retraction(self.admin2, approval_token)
        num_of_approvals = sum([val['has_approved'] for val in self.registration.retraction.approval_state.values()])
        assert_equal(num_of_approvals, 2)
        assert_true(self.registration.retraction.is_retracted)

    def test_one_approval_with_two_admins_stays_pending(self):
        self.admin2 = UserFactory()
        self.registration.contributors.append(self.admin2)
        self.registration.add_permission(self.admin2, 'admin', save=True)
        self.registration.is_public = True

        self.registration.retract_registration(self.user)
        self.registration.save()

        self.registration.reload()
        approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        assert_equal(self.registration.retraction.state, 'pending')
        self.registration.retraction.approve_retraction(self.user, approval_token)
        assert_equal(self.registration.retraction.state, 'pending')
        num_of_approvals = sum([val['has_approved'] for val in self.registration.retraction.approval_state.values()])

        assert_equal(num_of_approvals, 1)

    def test_pending_retract(self):
        self.registration.is_public = True
        self.registration.retract_registration(self.user, self.valid_justification)
        self.registration.save()

        self.registration.reload()
        assert_false(self.registration.retraction.is_retracted)
        assert_equal(self.registration.retraction.state, 'pending')
        assert_equal(self.registration.retraction.justification, self.valid_justification)
        assert_equal(self.registration.retraction.initiated_by, self.user)
        assert_equal(
            self.registration.retraction.initiation_date.date(),
            datetime.datetime.utcnow().date()
        )

    def test_long_justification_raises_validation_value_error(self):
        self.registration.is_public = True
        self.registration.save()
        with assert_raises(ValidationValueError):
            self.registration.retract_registration(self.user, self.invalid_justification)
            self.registration.save()
        self.registration.reload()
        assert_is_none(self.registration.retraction)

    def test_retract_private_registration_throws_type_error(self):
        with assert_raises(NodeStateError):
            self.registration.retract_registration(self.user, self.valid_justification)
            self.registration.save()

        self.registration.reload()
        assert_is_none(self.registration.retraction)

    def test_retract_public_non_registration_throws_type_error(self):
        self.project.is_public = True
        self.project.save()
        with assert_raises(NodeStateError):
            self.project.retract_registration(self.user, self.valid_justification)

        self.registration.reload()
        assert_is_none(self.registration.retraction)

    def test_set_public_registration_to_private_raises_node_exception(self):
        self.registration.is_public = True
        self.registration.save()
        with assert_raises(NodeStateError):
            self.registration.set_privacy('private')

        self.registration.reload()
        assert_true(self.registration.is_public)


class RegistrationRetractionViewsTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationRetractionViewsTestCase, self).setUp()
        self.admin_user = AuthUserFactory()
        self.admin_user.save()
        self.auth = self.admin_user.auth
        self.project = ProjectFactory(is_public=False, creator=self.admin_user)
        self.registration = RegistrationFactory(project=self.project)
        self.registration.is_public = True
        self.registration.save()

        self.retraction_post_url = self.registration.api_url_for('node_registration_retraction_post')
        self.retraction_get_url = self.registration.web_url_for('node_registration_retraction_get')
        self.justification = fake.sentence()

    def test_GET_retraction_page_when_pending_retraction_raises_400(self):
        self.registration.retract_registration(self.admin_user)
        self.registration.save()

        res = self.app.get(
            self.retraction_get_url,
            auth=self.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)

    def test_POST_retraction_to_private_registration_raises_400(self):
        self.registration.is_public = False
        self.registration.save()

        res = self.app.post_json(
            self.retraction_post_url,
             auth=self.auth,
             expect_errors=True,
        )

        assert_equal(res.status_code, 400)
        self.registration.reload()
        assert_is_none(self.registration.retraction)

    def test_POST_retraction_by_non_admin_retract_raises_401(self):
        res = self.app.post_json(self.retraction_post_url, expect_errors=True)

        assert_equals(res.status_code, 401)
        self.registration.reload()
        assert_is_none(self.registration.retraction)

    def test_POST_retraction_without_justification_raises_200(self):
        res = self.app.post_json(
            self.retraction_post_url,
             {'justification': ''},
             auth=self.auth,
        )

        assert_equal(res.status_code, 200)
        self.registration.reload()
        assert_false(self.registration.retraction.is_retracted)
        assert_equal(self.registration.retraction.state, 'pending')
        assert_is_none(self.registration.retraction.justification)
