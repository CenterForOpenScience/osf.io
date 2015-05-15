"""Tests related to embargoes of registrations"""

import datetime
import json

from nose.tools import *  #noqa
from tests.base import fake, OsfTestCase
from tests.factories import (
    AuthUserFactory, EmbargoFactory, RegistrationFactory, UserFactory,
    ProjectFactory,
)

from framework.exceptions import PermissionsError
from modularodm import Q
from modularodm.exceptions import ValidationValueError
from website.exceptions import (
    InvalidEmbargoDisapprovalToken, InvalidEmbargoApprovalToken, NodeStateError,
)
from website.models import Embargo, Node
from website.project.model import ensure_schemas


class RegistrationEmbargoModelsTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationEmbargoModelsTestCase, self).setUp()
        self.user = UserFactory()
        self.registration = RegistrationFactory(creator=self.user)
        self.embargo = EmbargoFactory(user=self.user)
        self.valid_embargo_end_date = datetime.date(2099, 1, 1)


    # Validator tests
    def test_invalid_state_raises_ValidationValueError(self):
        with assert_raises(ValidationValueError):
            self.embargo.state = 'not a valid state'
            self.embargo.save()

    # Node#_initiate_embargo tests
    def test__initiate_embargo_does_not_save_embargo(self):
        initial_count = Embargo.find().count()
        self.registration._initiate_embargo(
            self.user,
            self.valid_embargo_end_date,
            for_existing_registration=True
        )
        self.assertEqual(Embargo.find().count(), initial_count)

    def test__initiate_embargo_with_save_does_save_embargo(self):
        initial_count = Embargo.find().count()
        self.registration._initiate_embargo(
            self.user,
            self.valid_embargo_end_date,
            for_existing_registration=True,
            save=True
        )
        self.assertEqual(Embargo.find().count(), initial_count + 1)

    # Node#embargo_registration tests
    def test_embargo_from_non_admin_raises_PermissionsError(self):
        self.registration.remove_permission(self.user, 'admin')
        self.registration.save()
        self.registration.reload()
        with assert_raises(PermissionsError):
            self.registration.embargo_registration(self.user, self.valid_embargo_end_date)

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
        with assert_raises(InvalidEmbargoDisapprovalToken):
            self.registration.embargo.disapprove_embargo(self.user, fake.sentence())
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
        assert_equal(self.registration.embargo.state, Embargo.CANCELLED)
        assert_false(self.registration.pending_embargo)
        assert_false(self.registration.is_embargoed)

    def test_cancelling_embargo_deletes_parent_registration(self):
        self.registration.embargo_registration(
            self.user,
            (datetime.date.today() + datetime.timedelta(days=10))
        )
        self.registration.save()

        disapproval_token = self.registration.embargo.approval_state[self.user._id]['disapproval_token']
        self.registration.embargo.disapprove_embargo(self.user, disapproval_token)
        assert_equal(self.registration.embargo.state, Embargo.CANCELLED)
        assert_true(self.registration.is_deleted)

    def test_cancelling_embargo_for_existing_registration_does_not_delete_registration(self):
        self.registration.embargo_registration(
            self.user,
            (datetime.date.today() + datetime.timedelta(days=10)),
            for_existing_registration=True
        )
        self.registration.save()

        disapproval_token = self.registration.embargo.approval_state[self.user._id]['disapproval_token']
        self.registration.embargo.disapprove_embargo(self.user, disapproval_token)
        assert_equal(self.registration.embargo.state, Embargo.CANCELLED)
        assert_false(self.registration.is_deleted)

    # Embargo property tests
    def test_new_registration_is_pending_registration(self):
        self.registration.embargo_registration(
            self.user,
            (datetime.date.today() + datetime.timedelta(days=10))
        )
        self.registration.save()
        assert_true(self.registration.pending_registration)

    def test_existing_registration_is_not_pending_registration(self):
        self.registration.embargo_registration(
            self.user,
            (datetime.date.today() + datetime.timedelta(days=10)),
            for_existing_registration=True
        )
        self.registration.save()
        assert_false(self.registration.pending_registration)


class RegistrationEmbargoApprovalDisapprovalViewsTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationEmbargoApprovalDisapprovalViewsTestCase, self).setUp()
        self.user = AuthUserFactory()
        self.registration = RegistrationFactory(creator=self.user)

    # node_registration_embargo_approve tests
    def test_GET_from_unauthorized_user_raises_HTTPForbidden(self):
        unauthorized_user = AuthUserFactory()
        res = self.app.get(
            self.registration.web_url_for('node_registration_embargo_approve', token=fake.sentence()),
            auth=unauthorized_user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 403)

    def test_GET_approve_registration_without_embargo_raises_HTTPBad_Request(self):
        assert_false(self.registration.pending_embargo)
        res = self.app.get(
            self.registration.web_url_for('node_registration_embargo_approve', token=fake.sentence()),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_GET_approve_with_invalid_token_returns_HTTPBad_Request(self):
        self.registration.embargo_registration(
            self.user,
            (datetime.date.today() + datetime.timedelta(days=10))
        )
        self.registration.save()
        assert_true(self.registration.pending_embargo)

        res = self.app.get(
            self.registration.web_url_for('node_registration_embargo_approve', token=fake.sentence()),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_GET_approve_with_wrong_token_returns_HTTPBad_Request(self):
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

    def test_GET_approve_with_wrong_admins_token_returns_HTTPBad_Request(self):
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
        assert_true(self.registration.pending_embargo)
        assert_equal(res.status_code, 400)

    def test_GET_approve_with_valid_token_returns_redirect(self):
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
    def test_GET_from_unauthorized_user_returns_HTTPForbidden(self):
        unauthorized_user = AuthUserFactory()
        res = self.app.get(
            self.registration.web_url_for('node_registration_embargo_disapprove', token=fake.sentence()),
            auth=unauthorized_user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 403)

    def test_GET_disapprove_registration_without_embargo_HTTPBad_Request(self):
        assert_false(self.registration.pending_embargo)
        res = self.app.get(
            self.registration.web_url_for('node_registration_embargo_disapprove', token=fake.sentence()),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_GET_disapprove_with_invalid_token_returns_HTTPBad_Request(self):
        self.registration.embargo_registration(
            self.user,
            (datetime.date.today() + datetime.timedelta(days=10))
        )
        self.registration.save()
        assert_true(self.registration.pending_embargo)

        res = self.app.get(
            self.registration.web_url_for('node_registration_embargo_disapprove', token=fake.sentence()),
            auth=self.user.auth,
            expect_errors=True
        )
        self.registration.embargo.reload()
        assert_true(self.registration.pending_embargo)
        assert_equal(res.status_code, 400)

    def test_GET_disapprove_with_wrong_admins_token_returns_HTTPBad_Request(self):
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

    def test_GET_disapprove_with_valid_token_returns_redirect(self):
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
        assert_equal(self.registration.embargo.state, Embargo.CANCELLED)
        assert_false(self.registration.is_embargoed)
        assert_false(self.registration.pending_embargo)
        assert_equal(res.status_code, 302)


class RegistrationEmbargoViewsTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationEmbargoViewsTestCase, self).setUp()
        ensure_schemas()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.registration = RegistrationFactory(creator=self.user)

        current_month = datetime.datetime.now().strftime("%B")
        current_year = datetime.datetime.now().strftime("%Y")

        self.valid_make_public_payload = json.dumps({
            u'embargoEndDate': u'Fri, 01, {month} {year} 00:00:00 GMT'.format(
                month=current_month,
                year=current_year
            ),
            u'registrationChoice': 'Make registration public immediately',
            u'summary': unicode(fake.sentence())
        })
        self.valid_embargo_payload = json.dumps({
            u'embargoEndDate': u"Thu, 01 {month} {year} 05:00:00 GMT".format(
                month=current_month,
                year=str(int(current_year)+1)
            ),
            u'registrationChoice': 'Enter registration into embargo',
            u'summary': unicode(fake.sentence())
        })
        self.invalid_embargo_date_payload = json.dumps({
            u'embargoEndDate': u"Thu, 01 {month} {year} 05:00:00 GMT".format(
                month=current_month,
                year=str(int(current_year)-1)
            ),
            u'registrationChoice': 'Enter registration into embargo',
            u'summary': unicode(fake.sentence())
        })

    def test_POST_register_make_public_immediately_creates_public_registration(self):
        res = self.app.post(
            self.project.api_url_for('node_register_template_page_post', template=u'Open-Ended_Registration'),
            self.valid_make_public_payload,
            content_type='application/json',
            auth=self.user.auth
        )

        assert_equal(res.status_code, 201)
        registration_id = res.json['result'].strip('/')
        registration = Node.find_one(Q('_id', 'eq', registration_id))

        assert_true(registration.is_registration)
        assert_true(registration.is_public)

    def test_POST_register_embargo_is_not_public(self):
        res = self.app.post(
            self.project.api_url_for('node_register_template_page_post', template=u'Open-Ended_Registration'),
            self.valid_embargo_payload,
            content_type='application/json',
            auth=self.user.auth
        )

        assert_equal(res.status_code, 201)
        registration_id = res.json['result'].strip('/')
        registration = Node.find_one(Q('_id', 'eq', registration_id))

        assert_true(registration.is_registration)
        assert_false(registration.is_public)
        assert_true(registration.pending_registration)
        assert_is_not_none(registration.embargo)

    def test_POST_invalid_embargo_end_date_returns_HTTPBad_Request(self):
        res = self.app.post(
            self.project.api_url_for('node_register_template_page_post', template=u'Open-Ended_Registration'),
            self.invalid_embargo_date_payload,
            content_type='application/json',
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 400)
