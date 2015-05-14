"""Tests related to retraction of public registrations"""

import datetime

from nose.tools import *  # noqa
from tests.base import fake, OsfTestCase
from tests.factories import ProjectFactory, RegistrationFactory, UserFactory, AuthUserFactory

from modularodm.exceptions import ValidationValueError
from framework.exceptions import PermissionsError
from website.exceptions import (
    InvalidRetractionApprovalToken, InvalidRetractionDisapprovalToken,
    NodeStateError,
)
from website.models import Retraction


class RegistrationRetractionModelsTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationRetractionModelsTestCase, self).setUp()
        self.user = UserFactory()
        self.registration = RegistrationFactory(creator=self.user, is_public=True)
        self.valid_justification = fake.sentence()
        self.invalid_justification = fake.text(max_nb_chars=3000)

    # Validator tests
    def test_invalid_state_raises_ValidationValueError(self):
        self.registration.retract_registration(self.user)
        with assert_raises(ValidationValueError):
            self.registration.retraction.state = 'invalid_state'
            self.registration.retraction.save()

    def test_set_public_registration_to_private_raises_NodeStateException(self):
        self.registration.save()
        with assert_raises(NodeStateError):
            self.registration.set_privacy('private')
        self.registration.reload()

        assert_true(self.registration.is_public)

    # Backref tests
    def test_retraction_initiator_has_backref(self):
        self.registration.retract_registration(self.user, self.valid_justification)
        self.registration.save()
        self.registration.reload()
        assert_equal(len(self.user.retraction__retracted), 1)

    # Node#retract_registration tests
    def test_pending_retract(self):
        self.registration.retract_registration(self.user, self.valid_justification)
        self.registration.save()
        self.registration.reload()

        assert_false(self.registration.retraction.is_retracted)
        assert_equal(self.registration.retraction.state, Retraction.PENDING)
        assert_equal(self.registration.retraction.justification, self.valid_justification)
        assert_equal(self.registration.retraction.initiated_by, self.user)
        assert_equal(
            self.registration.retraction.initiation_date.date(),
            datetime.datetime.utcnow().date()
        )

    def test_long_justification_raises_ValidationValueError(self):
        with assert_raises(ValidationValueError):
            self.registration.retract_registration(self.user, self.invalid_justification)
            self.registration.save()
        self.registration.reload()
        assert_is_none(self.registration.retraction)

    def test_retract_private_registration_raises_NodeStateError(self):
        self.registration.is_public = False
        with assert_raises(NodeStateError):
            self.registration.retract_registration(self.user, self.valid_justification)
            self.registration.save()
        self.registration.reload()
        assert_is_none(self.registration.retraction)

    def test_retract_public_non_registration_raises_NodeStateError(self):
        project = ProjectFactory(is_public=True, creator=self.user)
        project.save()
        with assert_raises(NodeStateError):
            project.retract_registration(self.user, self.valid_justification)

        project.reload()
        assert_is_none(project.retraction)

    def test_retraction_of_registration_pending_embargo_cancels_embargo(self):
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
        assert_equal(self.registration.embargo.state, Retraction.CANCELLED)

    def test_retraction_of_registration_in_active_embargo_cancels_embargo(self):
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
        assert_equal(self.registration.embargo.state, Retraction.CANCELLED)

    # Retraction#approve_retraction_tests
    def test_invalid_approval_token_raises_InvalidRetractionApprovalToken(self):
        self.registration.retract_registration(self.user)
        self.registration.save()
        assert_true(self.registration.pending_retraction)

        with assert_raises(InvalidRetractionApprovalToken):
            self.registration.retraction.approve_retraction(self.user, fake.sentence())
        assert_true(self.registration.pending_retraction)
        assert_false(self.registration.is_retracted)

    def test_non_admin_approval_token_raises_PermissionsError(self):
        non_admin = UserFactory()
        self.registration.retract_registration(self.user)
        self.registration.save()
        assert_true(self.registration.pending_retraction)

        approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        with assert_raises(PermissionsError):
            self.registration.retraction.approve_retraction(non_admin, approval_token)
        assert_true(self.registration.pending_retraction)
        assert_false(self.registration.is_retracted)

    def test_one_approval_with_one_admin_retracts(self):
        self.registration.retract_registration(self.user)
        self.registration.save()

        approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        assert_equal(self.registration.retraction.state, Retraction.PENDING)
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
        assert_equal(self.registration.embargo.state, Retraction.CANCELLED)

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
        assert_equal(self.registration.embargo.state, Retraction.CANCELLED)

    def test_two_approvals_with_two_admins_retracts(self):
        self.admin2 = UserFactory()
        self.registration.contributors.append(self.admin2)
        self.registration.add_permission(self.admin2, 'admin', save=True)
        self.registration.retract_registration(self.user)
        self.registration.save()
        self.registration.reload()

        # First admin approves
        approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        self.registration.retraction.approve_retraction(self.user, approval_token)
        assert_equal(self.registration.retraction.state, Retraction.PENDING)
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

        self.registration.retract_registration(self.user)
        self.registration.save()
        self.registration.reload()

        approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        assert_equal(self.registration.retraction.state, Retraction.PENDING)
        self.registration.retraction.approve_retraction(self.user, approval_token)
        assert_equal(self.registration.retraction.state, Retraction.PENDING)
        num_of_approvals = sum([val['has_approved'] for val in self.registration.retraction.approval_state.values()])
        assert_equal(num_of_approvals, 1)

    # Retraction#disapprove_retraction tests
    def test_invalid_disapproval_token_raises_InvalidRetractionDisapprovalToken(self):
        self.registration.retract_registration(self.user)
        self.registration.save()
        assert_true(self.registration.pending_retraction)

        with assert_raises(InvalidRetractionDisapprovalToken):
            self.registration.retraction.disapprove_retraction(self.user, fake.sentence())
        assert_true(self.registration.pending_retraction)
        assert_false(self.registration.is_retracted)

    def test_non_admin_disapproval_token_raises_PermissionsError(self):
        non_admin = UserFactory()
        self.registration.retract_registration(self.user)
        self.registration.save()
        assert_true(self.registration.pending_retraction)

        disapproval_token = self.registration.retraction.approval_state[self.user._id]['disapproval_token']
        with assert_raises(PermissionsError):
            self.registration.retraction.disapprove_retraction(non_admin, disapproval_token)
        assert_true(self.registration.pending_retraction)
        assert_false(self.registration.is_retracted)

    def test_one_disapproval_cancels_retraction(self):
        self.registration.retract_registration(self.user)
        self.registration.save()
        self.registration.reload()

        disapproval_token = self.registration.retraction.approval_state[self.user._id]['disapproval_token']
        assert_equal(self.registration.retraction.state, Retraction.PENDING)
        self.registration.retraction.disapprove_retraction(self.user, disapproval_token)
        assert_equal(self.registration.retraction.state, Retraction.CANCELLED)

    # Retraction property tests
    def test_new_retraction_is_pending_retraction(self):
        self.registration.retract_registration(self.user)
        assert_true(self.registration.pending_retraction)
        assert_false(self.registration.is_retracted)


class RegistrationRetractionApprovalDisapprovalViewsTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationRetractionApprovalDisapprovalViewsTestCase, self).setUp()
        self.user = AuthUserFactory()
        self.auth = self.user.auth
        self.registration = RegistrationFactory(is_public=True, creator=self.user)

    # node_registration_retraction_approve_tests
    def test_GET_approve_from_unauthorized_user_raises_HTTPForbidden(self):
        unauthorized_user = AuthUserFactory()

        res = self.app.get(
            self.registration.web_url_for('node_registration_retraction_approve', token=fake.sentence()),
            auth=unauthorized_user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 403)

    def test_GET_approve_registration_without_retraction_returns_HTTPBad_Request(self):
        assert_false(self.registration.pending_retraction)

        res = self.app.get(
            self.registration.web_url_for('node_registration_retraction_approve', token=fake.sentence()),
            auth=self.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_GET_approve_with_invalid_token_returns_HTTPBad_Request(self):
        self.registration.retract_registration(self.user)
        self.registration.save()
        assert_true(self.registration.pending_retraction)

        res = self.app.get(
            self.registration.web_url_for('node_registration_retraction_approve', token=fake.sentence()),
            auth=self.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_GET_approve_with_valid_token_returns_redirect(self):
        self.registration.retract_registration(self.user)
        self.registration.save()
        assert_true(self.registration.pending_retraction)

        approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        res = self.app.get(
            self.registration.web_url_for('node_registration_retraction_approve', token=approval_token),
            auth=self.auth
        )
        self.registration.retraction.reload()
        assert_true(self.registration.is_retracted)
        assert_false(self.registration.pending_retraction)
        assert_equal(res.status_code, 302)

    def test_GET_approve_with_wrong_admins_token_returns_HTTPBad_Request(self):
        user2 = AuthUserFactory()
        self.registration.contributors.append(user2)
        self.registration.add_permission(user2, 'admin', save=True)
        self.registration.retract_registration(self.user)
        self.registration.save()
        assert_true(self.registration.pending_retraction)
        assert_equal(len(self.registration.retraction.approval_state), 2)

        wrong_approval_token = self.registration.retraction.approval_state[user2._id]['approval_token']
        res = self.app.get(
            self.registration.web_url_for('node_registration_retraction_approve', token=wrong_approval_token),
            auth=self.auth,
            expect_errors=True
        )
        assert_true(self.registration.pending_retraction)
        assert_equal(res.status_code, 400)

    # node_registration_retraction_disapprove_tests
    def test_GET_disapprove_from_unauthorized_user_raises_HTTPForbidden(self):
        unauthorized_user = AuthUserFactory()

        res = self.app.get(
            self.registration.web_url_for('node_registration_retraction_disapprove', token=fake.sentence()),
            auth=unauthorized_user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 403)

    def test_GET_disapprove_registration_without_retraction_returns_HTTPBad_Request(self):
        assert_false(self.registration.pending_retraction)

        res = self.app.get(
            self.registration.web_url_for('node_registration_retraction_disapprove', token=fake.sentence()),
            auth=self.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_GET_disapprove_with_invalid_token_returns_HTTPBad_Request(self):
        self.registration.retract_registration(self.user)
        self.registration.save()
        assert_true(self.registration.pending_retraction)

        res = self.app.get(
            self.registration.web_url_for('node_registration_retraction_disapprove', token=fake.sentence()),
            auth=self.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_GET_disapprove_with_wrong_admins_token_returns_HTTPBad_Request(self):
        user2 = AuthUserFactory()
        self.registration.contributors.append(user2)
        self.registration.add_permission(user2, 'admin', save=True)
        self.registration.retract_registration(self.user)
        self.registration.save()
        assert_true(self.registration.pending_retraction)
        assert_equal(len(self.registration.retraction.approval_state), 2)

        wrong_disapproval_token = self.registration.retraction.approval_state[user2._id]['disapproval_token']
        res = self.app.get(
            self.registration.web_url_for('node_registration_retraction_disapprove', token=wrong_disapproval_token),
            auth=self.auth,
            expect_errors=True
        )
        assert_true(self.registration.pending_retraction)
        assert_equal(res.status_code, 400)

    def test_GET_disapprove_with_valid_token_returns_redirect(self):
        self.registration.retract_registration(self.user)
        self.registration.save()
        assert_true(self.registration.pending_retraction)

        disapproval_token = self.registration.retraction.approval_state[self.user._id]['disapproval_token']
        res = self.app.get(
            self.registration.web_url_for('node_registration_retraction_disapprove', token=disapproval_token),
            auth=self.auth,
        )
        self.registration.retraction.reload()
        assert_false(self.registration.is_retracted)
        assert_false(self.registration.pending_retraction)
        assert_equal(self.registration.retraction.state, Retraction.CANCELLED)
        assert_equal(res.status_code, 302)


class RegistrationRetractionViewsTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationRetractionViewsTestCase, self).setUp()
        self.user = AuthUserFactory()
        self.auth = self.user.auth
        self.registration = RegistrationFactory(creator=self.user, is_public=True)

        self.retraction_post_url = self.registration.api_url_for('node_registration_retraction_post')
        self.retraction_get_url = self.registration.web_url_for('node_registration_retraction_get')
        self.justification = fake.sentence()

    def test_GET_retraction_page_when_pending_retraction_returns_HTTPBad_Request(self):
        self.registration.retract_registration(self.user)
        self.registration.save()

        res = self.app.get(
            self.retraction_get_url,
            auth=self.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)

    def test_POST_retraction_to_private_registration_returns_HTTPBad_request(self):
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

    def test_POST_retraction_by_non_admin_retract_HTTPUnauthorized(self):
        res = self.app.post_json(self.retraction_post_url, expect_errors=True)
        assert_equals(res.status_code, 401)
        self.registration.reload()
        assert_is_none(self.registration.retraction)

    def test_POST_retraction_without_justification_returns_HTTPOK(self):
        res = self.app.post_json(
            self.retraction_post_url,
            {'justification': ''},
            auth=self.auth,
        )
        assert_equal(res.status_code, 200)
        self.registration.reload()
        assert_false(self.registration.retraction.is_retracted)
        assert_equal(self.registration.retraction.state, Retraction.PENDING)
        assert_is_none(self.registration.retraction.justification)
