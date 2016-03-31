"""Tests related to embargoes of registrations"""
import datetime
import httplib as http
import json

from modularodm import Q

import mock
from nose.tools import *  # noqa
from tests.base import fake, OsfTestCase
from tests.factories import (
    AuthUserFactory, EmbargoFactory, NodeFactory, ProjectFactory,
    RegistrationFactory, UserFactory, UnconfirmedUserFactory, DraftRegistrationFactory
)
from modularodm.exceptions import ValidationValueError

from framework.exceptions import PermissionsError
from framework.auth import Auth
from website.exceptions import (
    InvalidSanctionRejectionToken, InvalidSanctionApprovalToken, NodeStateError,
)
from website import tokens
from website.models import Embargo, Node, User
from website.project.model import ensure_schemas
from website.project.sanctions import PreregCallbackMixin
from website.util import permissions

DUMMY_TOKEN = tokens.encode({
    'dummy': 'token'
})


class RegistrationEmbargoModelsTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationEmbargoModelsTestCase, self).setUp()
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.registration = RegistrationFactory(project=self.project)
        self.embargo = EmbargoFactory(user=self.user)
        self.valid_embargo_end_date = datetime.datetime.utcnow() + datetime.timedelta(days=3)

    # Node#_initiate_embargo tests
    def test__initiate_embargo_saves_embargo(self):
        initial_count = Embargo.find().count()
        self.registration._initiate_embargo(
            self.user,
            self.valid_embargo_end_date,
            for_existing_registration=True
        )
        assert_equal(Embargo.find().count(), initial_count + 1)

    def test_state_can_be_set_to_complete(self):
        embargo = EmbargoFactory()
        embargo.state = Embargo.COMPLETED
        embargo.save()  # should pass validation
        assert_equal(embargo.state, Embargo.COMPLETED)

    def test__initiate_embargo_does_not_create_tokens_for_unregistered_admin(self):
        unconfirmed_user = UnconfirmedUserFactory()
        self.registration.contributors.append(unconfirmed_user)
        self.registration.add_permission(unconfirmed_user, 'admin', save=True)
        assert_true(self.registration.has_permission(unconfirmed_user, 'admin'))

        embargo = self.registration._initiate_embargo(
            self.user,
            self.valid_embargo_end_date,
            for_existing_registration=True
        )
        assert_true(self.user._id in embargo.approval_state)
        assert_false(unconfirmed_user._id in embargo.approval_state)

    def test__initiate_embargo_adds_admins_on_child_nodes(self):
        project_admin = UserFactory()
        project_non_admin = UserFactory()
        child_admin = UserFactory()
        child_non_admin = UserFactory()
        grandchild_admin = UserFactory()

        project = ProjectFactory(creator=project_admin)
        project.add_contributor(project_non_admin, auth=Auth(project.creator), save=True)

        child = NodeFactory(creator=child_admin, parent=project)
        child.add_contributor(child_non_admin, auth=Auth(project.creator), save=True)

        grandchild = NodeFactory(creator=grandchild_admin, parent=child)  # noqa

        embargo = project._initiate_embargo(
            project.creator,
            self.valid_embargo_end_date,
            for_existing_registration=True
        )
        assert_in(project_admin._id, embargo.approval_state)
        assert_in(child_admin._id, embargo.approval_state)
        assert_in(grandchild_admin._id, embargo.approval_state)

        assert_not_in(project_non_admin._id, embargo.approval_state)
        assert_not_in(child_non_admin._id, embargo.approval_state)

    def test__initiate_embargo_with_save_does_save_embargo(self):
        initial_count = Embargo.find().count()
        self.registration._initiate_embargo(
            self.user,
            self.valid_embargo_end_date,
            for_existing_registration=True,
        )
        assert_equal(Embargo.find().count(), initial_count + 1)

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
                datetime.datetime(1999, 1, 1)
            )

    def test_embargo_end_date_today_raises_ValidationValueError(self):
        with assert_raises(ValidationValueError):
            self.registration.embargo_registration(
                self.user,
                datetime.datetime.utcnow()
            )

    def test_embargo_end_date_in_far_future_raises_ValidationValueError(self):
        with assert_raises(ValidationValueError):
            self.registration.embargo_registration(
                self.user,
                datetime.datetime(2099, 1, 1)
            )

    def test_embargo_with_valid_end_date_starts_pending_embargo(self):
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

    def test_embargo_public_project_makes_private_pending_embargo(self):
        self.registration.is_public = True
        assert_true(self.registration.is_public)
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)
        assert_false(self.registration.is_public)

    def test_embargo_non_registration_raises_NodeStateError(self):
        self.registration.is_registration = False
        self.registration.save()
        with assert_raises(NodeStateError):
            self.registration.embargo_registration(
                self.user,
                datetime.datetime.utcnow() + datetime.timedelta(days=10)
            )
        assert_false(self.registration.is_pending_embargo)

    # Embargo#approve_embargo tests
    def test_invalid_approval_token_raises_InvalidSanctionApprovalToken(self):
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        invalid_approval_token = 'not a real token'
        with assert_raises(InvalidSanctionApprovalToken):
            self.registration.embargo.approve_embargo(self.user, invalid_approval_token)
        assert_true(self.registration.is_pending_embargo)

    def test_non_admin_approval_token_raises_PermissionsError(self):
        non_admin = UserFactory()
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        approval_token = self.registration.embargo.approval_state[self.user._id]['approval_token']
        with assert_raises(PermissionsError):
            self.registration.embargo.approve_embargo(non_admin, approval_token)
        assert_true(self.registration.is_pending_embargo)

    def test_one_approval_with_one_admin_embargoes(self):
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        approval_token = self.registration.embargo.approval_state[self.user._id]['approval_token']
        self.registration.embargo.approve_embargo(self.user, approval_token)
        assert_true(self.registration.embargo_end_date)
        assert_false(self.registration.is_pending_embargo)

    def test_approval_adds_to_parent_projects_log(self):
        initial_project_logs = len(self.registration.registered_from.logs)
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        self.registration.save()

        approval_token = self.registration.embargo.approval_state[self.user._id]['approval_token']
        self.registration.embargo.approve_embargo(self.user, approval_token)
        # Logs: Created, registered, embargo initiated, embargo approved
        assert_equal(len(self.registration.registered_from.logs), initial_project_logs + 2)

    def test_one_approval_with_two_admins_stays_pending(self):
        admin2 = UserFactory()
        self.registration.contributors.append(admin2)
        self.registration.add_permission(admin2, 'admin', save=True)
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        self.registration.save()

        # First admin approves
        approval_token = self.registration.embargo.approval_state[self.user._id]['approval_token']
        self.registration.embargo.approve_embargo(self.user, approval_token)
        assert_true(self.registration.is_pending_embargo)
        num_of_approvals = sum([val['has_approved'] for val in self.registration.embargo.approval_state.values()])
        assert_equal(num_of_approvals, 1)

        # Second admin approves
        approval_token = self.registration.embargo.approval_state[admin2._id]['approval_token']
        self.registration.embargo.approve_embargo(admin2, approval_token)
        assert_true(self.registration.embargo_end_date)
        assert_false(self.registration.is_pending_embargo)
        num_of_approvals = sum([val['has_approved'] for val in self.registration.embargo.approval_state.values()])
        assert_equal(num_of_approvals, 2)

    # Embargo#disapprove_embargo tests
    def test_invalid_rejection_token_raises_InvalidSanctionRejectionToken(self):
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)
        with assert_raises(InvalidSanctionRejectionToken):
            self.registration.embargo.disapprove_embargo(self.user, fake.sentence())
        assert_true(self.registration.is_pending_embargo)

    def test_non_admin_rejection_token_raises_PermissionsError(self):
        non_admin = UserFactory()
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        rejection_token = self.registration.embargo.approval_state[self.user._id]['rejection_token']
        with assert_raises(PermissionsError):
            self.registration.embargo.disapprove_embargo(non_admin, rejection_token)
        assert_true(self.registration.is_pending_embargo)

    def test_one_disapproval_cancels_embargo(self):
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        rejection_token = self.registration.embargo.approval_state[self.user._id]['rejection_token']
        self.registration.embargo.disapprove_embargo(self.user, rejection_token)
        assert_equal(self.registration.embargo.state, Embargo.REJECTED)
        assert_false(self.registration.is_pending_embargo)

    def test_disapproval_adds_to_parent_projects_log(self):
        initial_project_logs = len(self.registration.registered_from.logs)
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        self.registration.save()

        rejection_token = self.registration.embargo.approval_state[self.user._id]['rejection_token']
        registered_from = self.registration.registered_from
        self.registration.embargo.disapprove_embargo(self.user, rejection_token)
        # Logs: Created, registered, embargo initiated, embargo cancelled
        assert_equal(len(registered_from.logs), initial_project_logs + 2)

    def test_cancelling_embargo_deletes_parent_registration(self):
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        self.registration.save()

        rejection_token = self.registration.embargo.approval_state[self.user._id]['rejection_token']
        self.registration.embargo.disapprove_embargo(self.user, rejection_token)
        assert_equal(self.registration.embargo.state, Embargo.REJECTED)
        assert_true(self.registration.is_deleted)

    def test_cancelling_embargo_deletes_component_registrations(self):
        component = NodeFactory(
            creator=self.user,
            parent=self.project,
            title='Component'
        )
        subcomponent = NodeFactory(
            creator=self.user,
            parent=component,
            title='Subcomponent'
        )
        project_registration = RegistrationFactory(project=self.project)
        component_registration = project_registration.nodes[0]
        subcomponent_registration = component_registration.nodes[0]
        project_registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        project_registration.save()

        rejection_token = project_registration.embargo.approval_state[self.user._id]['rejection_token']
        project_registration.embargo.disapprove_embargo(self.user, rejection_token)
        assert_equal(project_registration.embargo.state, Embargo.REJECTED)
        assert_true(project_registration.is_deleted)
        assert_true(component_registration.is_deleted)
        assert_true(subcomponent_registration.is_deleted)

    def test_cancelling_embargo_for_existing_registration_does_not_delete_registration(self):
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10),
            for_existing_registration=True
        )
        self.registration.save()

        rejection_token = self.registration.embargo.approval_state[self.user._id]['rejection_token']
        self.registration.embargo.disapprove_embargo(self.user, rejection_token)
        assert_equal(self.registration.embargo.state, Embargo.REJECTED)
        assert_false(self.registration.is_deleted)

    def test_rejecting_embargo_for_existing_registration_does_not_deleted_component_registrations(self):
        component = NodeFactory(
            creator=self.user,
            parent=self.project,
            title='Component'
        )
        subcomponent = NodeFactory(
            creator=self.user,
            parent=component,
            title='Subcomponent'
        )
        project_registration = RegistrationFactory(project=self.project)
        component_registration = project_registration.nodes[0]
        subcomponent_registration = component_registration.nodes[0]
        project_registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10),
            for_existing_registration=True
        )

        rejection_token = project_registration.embargo.approval_state[self.user._id]['rejection_token']
        project_registration.embargo.disapprove_embargo(self.user, rejection_token)
        project_registration.save()
        assert_equal(project_registration.embargo.state, Embargo.REJECTED)
        assert_false(project_registration.is_deleted)
        assert_false(component_registration.is_deleted)
        assert_false(subcomponent_registration.is_deleted)

    # Embargo property tests
    def test_new_registration_is_pending_registration(self):
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo_for_existing_registration)

    def test_existing_registration_is_not_pending_registration(self):
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10),
            for_existing_registration=True
        )
        self.registration.save()
        assert_false(self.registration.is_pending_embargo_for_existing_registration)

    def test_on_complete_notify_initiator(self):
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10),
            notify_initiator_on_complete=True
        )
        self.registration.save()
        with mock.patch.object(PreregCallbackMixin, '_notify_initiator') as mock_notify:
            self.registration.embargo._on_complete(self.user)
        mock_notify.assert_called()


class RegistrationWithChildNodesEmbargoModelTestCase(OsfTestCase):

    def setUp(self):
        super(RegistrationWithChildNodesEmbargoModelTestCase, self).setUp()
        self.user = AuthUserFactory()
        self.auth = self.user.auth
        self.valid_embargo_end_date = datetime.datetime.utcnow() + datetime.timedelta(days=3)
        self.project = ProjectFactory(title='Root', is_public=False, creator=self.user)
        self.component = NodeFactory(
            creator=self.user,
            parent=self.project,
            title='Component'
        )
        self.subproject = ProjectFactory(
            creator=self.user,
            parent=self.project,
            title='Subproject'
        )
        self.subproject_component = NodeFactory(
            creator=self.user,
            parent=self.subproject,
            title='Subcomponent'
        )
        self.registration = RegistrationFactory(project=self.project)
        # Reload the registration; else tests won't catch failures to save
        self.registration.reload()

    def test_approval_embargoes_descendant_nodes(self):
        # Initiate embargo for parent registration
        self.registration.embargo_registration(
            self.user,
            self.valid_embargo_end_date
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        # Ensure descendant nodes are pending embargo
        descendants = self.registration.get_descendants_recursive()
        for node in descendants:
            assert_true(node.is_pending_embargo)

        # Approve parent registration's embargo
        approval_token = self.registration.embargo.approval_state[self.user._id]['approval_token']
        self.registration.embargo.approve_embargo(self.user, approval_token)
        assert_true(self.registration.embargo.embargo_end_date)

        # Ensure descendant nodes are in embargo
        descendants = self.registration.get_descendants_recursive()
        for node in descendants:
            assert_true(node.embargo_end_date)

    def test_disapproval_cancels_embargo_on_descendant_nodes(self):
        # Initiate embargo on parent registration
        self.registration.embargo_registration(
            self.user,
            self.valid_embargo_end_date
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        # Ensure descendant nodes are pending embargo
        descendants = self.registration.get_descendants_recursive()
        for node in descendants:
            assert_true(node.is_pending_embargo)

        # Disapprove parent registration's embargo
        rejection_token = self.registration.embargo.approval_state[self.user._id]['rejection_token']
        self.registration.embargo.disapprove_embargo(self.user, rejection_token)
        assert_false(self.registration.is_pending_embargo)
        assert_equal(self.registration.embargo.state, Embargo.REJECTED)

        # Ensure descendant nodes' embargoes are cancelled
        descendants = self.registration.get_descendants_recursive()
        for node in descendants:
            assert_false(node.is_pending_embargo)
            assert_false(node.embargo_end_date)


class RegistrationEmbargoApprovalDisapprovalViewsTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationEmbargoApprovalDisapprovalViewsTestCase, self).setUp()
        self.user = AuthUserFactory()
        self.registration = RegistrationFactory(creator=self.user)

    # node_registration_embargo_approve tests
    def test_GET_from_unauthorized_user_raises_HTTPForbidden(self):
        unauthorized_user = AuthUserFactory()
        res = self.app.get(
            self.registration.web_url_for('view_project', token=DUMMY_TOKEN),
            auth=unauthorized_user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 403)

    def test_GET_approve_registration_without_embargo_raises_HTTPBad_Request(self):
        assert_false(self.registration.is_pending_embargo)
        res = self.app.get(
            self.registration.web_url_for('view_project', token=DUMMY_TOKEN),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_GET_approve_with_invalid_token_returns_HTTPBad_Request(self):
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        res = self.app.get(
            self.registration.web_url_for('view_project', token=DUMMY_TOKEN),
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
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        wrong_approval_token = self.registration.embargo.approval_state[admin2._id]['approval_token']
        res = self.app.get(
            self.registration.web_url_for('view_project', token=wrong_approval_token),
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
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        wrong_approval_token = self.registration.embargo.approval_state[admin2._id]['approval_token']
        res = self.app.get(
            self.registration.web_url_for('view_project', token=wrong_approval_token),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_true(self.registration.is_pending_embargo)
        assert_equal(res.status_code, 400)

    @mock.patch('flask.redirect')
    def test_GET_approve_with_valid_token_redirects(self, mock_redirect):
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        approval_token = self.registration.embargo.approval_state[self.user._id]['approval_token']
        self.app.get(
            self.registration.web_url_for('view_project', token=approval_token),
            auth=self.user.auth,
        )
        self.registration.embargo.reload()
        assert_true(self.registration.embargo_end_date)
        assert_false(self.registration.is_pending_embargo)
        assert_true(mock_redirect.called_with(self.registration.web_url_for('view_project')))

    def test_GET_from_unauthorized_user_returns_HTTPForbidden(self):
        unauthorized_user = AuthUserFactory()
        res = self.app.get(
            self.registration.web_url_for('view_project', token=DUMMY_TOKEN),
            auth=unauthorized_user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 403)

    def test_GET_disapprove_registration_without_embargo_HTTPBad_Request(self):
        assert_false(self.registration.is_pending_embargo)
        res = self.app.get(
            self.registration.web_url_for('view_project', token=DUMMY_TOKEN),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_GET_disapprove_with_invalid_token_returns_HTTPBad_Request(self):
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        res = self.app.get(
            self.registration.web_url_for('view_project', token=DUMMY_TOKEN),
            auth=self.user.auth,
            expect_errors=True
        )
        self.registration.embargo.reload()
        assert_true(self.registration.is_pending_embargo)
        assert_equal(res.status_code, 400)

    def test_GET_disapprove_with_wrong_admins_token_returns_HTTPBad_Request(self):
        admin2 = UserFactory()
        self.registration.contributors.append(admin2)
        self.registration.add_permission(admin2, 'admin', save=True)
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        wrong_rejection_token = self.registration.embargo.approval_state[admin2._id]['rejection_token']
        res = self.app.get(
            self.registration.web_url_for('view_project', token=wrong_rejection_token),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_true(self.registration.is_pending_embargo)
        assert_equal(res.status_code, 400)

    def test_GET_disapprove_with_valid(self):
        project = ProjectFactory(creator=self.user)
        registration = RegistrationFactory(project=project)
        registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        registration.save()
        assert_true(registration.is_pending_embargo)

        rejection_token = registration.embargo.approval_state[self.user._id]['rejection_token']

        res = self.app.get(
            registration.registered_from.web_url_for('view_project', token=rejection_token),
            auth=self.user.auth,
        )
        registration.embargo.reload()
        assert_equal(registration.embargo.state, Embargo.REJECTED)
        assert_false(registration.is_pending_embargo)
        assert_equal(res.status_code, 200)
        assert_equal(project.web_url_for('view_project'), res.request.path)

    def test_GET_disapprove_for_existing_registration_returns_200(self):
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10),
            for_existing_registration=True
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        rejection_token = self.registration.embargo.approval_state[self.user._id]['rejection_token']
        res = self.app.get(
            self.registration.web_url_for('view_project', token=rejection_token),
            auth=self.user.auth,
        )
        self.registration.embargo.reload()
        assert_equal(self.registration.embargo.state, Embargo.REJECTED)
        assert_false(self.registration.is_pending_embargo)
        assert_equal(res.status_code, 200)
        assert_equal(res.request.path, self.registration.web_url_for('view_project'))


class RegistrationEmbargoViewsTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationEmbargoViewsTestCase, self).setUp()
        ensure_schemas()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.draft = DraftRegistrationFactory(branched_from=self.project)
        self.registration = RegistrationFactory(project=self.project, creator=self.user)

        current_month = datetime.datetime.now().strftime("%B")
        current_year = datetime.datetime.now().strftime("%Y")

        self.valid_make_public_payload = json.dumps({
            u'embargoEndDate': u'Fri, 01, {month} {year} 00:00:00 GMT'.format(
                month=current_month,
                year=current_year
            ),
            u'registrationChoice': 'immediate',
            u'summary': unicode(fake.sentence())
        })
        valid_date = datetime.datetime.now() + datetime.timedelta(days=180)
        self.valid_embargo_payload = json.dumps({
            u'embargoEndDate': unicode(valid_date.strftime('%a, %d, %B %Y %H:%M:%S')) + u' GMT',
            u'registrationChoice': 'embargo',
            u'summary': unicode(fake.sentence())
        })
        self.invalid_embargo_date_payload = json.dumps({
            u'embargoEndDate': u"Thu, 01 {month} {year} 05:00:00 GMT".format(
                month=current_month,
                year=str(int(current_year)-1)
            ),
            u'registrationChoice': 'embargo',
            u'summary': unicode(fake.sentence())
        })

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_register_draft_without_embargo_creates_registration_approval(self, mock_enqueue):
        res = self.app.post(
            self.project.api_url_for('register_draft_registration', draft_id=self.draft._id),
            self.valid_make_public_payload,
            content_type='application/json',
            auth=self.user.auth
        )
        assert_equal(res.status_code, 202)

        registration = Node.find().sort('-registered_date')[0]

        assert_true(registration.is_registration)
        assert_not_equal(registration.registration_approval, None)

    # Regression test for https://openscience.atlassian.net/browse/OSF-5039
    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_POST_register_make_public_immediately_creates_private_pending_registration_for_public_project(self, mock_enqueue):
        self.project.is_public = True
        self.project.save()
        component = NodeFactory(
            creator=self.user,
            parent=self.project,
            title='Component',
            is_public=True
        )
        subproject = ProjectFactory(
            creator=self.user,
            parent=self.project,
            title='Subproject',
            is_public=True
        )
        subproject_component = NodeFactory(
            creator=self.user,
            parent=subproject,
            title='Subcomponent',
            is_public=True
        )
        res = self.app.post(
            self.project.api_url_for('register_draft_registration', draft_id=self.draft._id),
            self.valid_make_public_payload,
            content_type='application/json',
            auth=self.user.auth
        )
        self.project.reload()
        assert_equal(res.status_code, 202)
        assert_equal(res.json['urls']['registrations'], self.project.web_url_for('node_registrations'))


        # Last node directly registered from self.project
        registration = Node.find(
            Q('registered_from', 'eq', self.project)
        ).sort('-registered_date')[0]

        assert_true(registration.is_registration)
        assert_false(registration.is_public)
        for node in registration.get_descendants_recursive():
            assert_true(node.is_registration)
            assert_false(node.is_public)

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_POST_register_make_public_does_not_make_children_public(self, mock_enqueue):
        component = NodeFactory(
            creator=self.user,
            parent=self.project,
            title='Component'
        )
        subproject = ProjectFactory(
            creator=self.user,
            parent=self.project,
            title='Subproject'
        )
        subproject_component = NodeFactory(
            creator=self.user,
            parent=subproject,
            title='Subcomponent'
        )

        res = self.app.post(
            self.project.api_url_for('register_draft_registration', draft_id=self.draft._id),
            self.valid_make_public_payload,
            content_type='application/json',
            auth=self.user.auth
        )
        self.project.reload()
        # Last node directly registered from self.project
        registration = self.project.registrations_all[-1]
        assert_false(registration.is_public)
        for node in registration.get_descendants_recursive():
            assert_true(node.is_registration)
            assert_false(node.is_public)

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_POST_register_embargo_is_not_public(self, mock_enqueue):
        res = self.app.post(
            self.project.api_url_for('register_draft_registration', draft_id=self.draft._id),
            self.valid_embargo_payload,
            content_type='application/json',
            auth=self.user.auth
        )

        assert_equal(res.status_code, 202)

        registration = Node.find().sort('-registered_date')[0]

        assert_true(registration.is_registration)
        assert_false(registration.is_public)
        assert_true(registration.is_pending_embargo_for_existing_registration)
        assert_is_not_none(registration.embargo)

    # Regression test for https://openscience.atlassian.net/browse/OSF-5071
    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_POST_register_embargo_does_not_make_project_or_children_public(self, mock_enqueue):
        self.project.is_public = True
        self.project.save()
        component = NodeFactory(
            creator=self.user,
            parent=self.project,
            title='Component',
            is_public=True
        )
        subproject = ProjectFactory(
            creator=self.user,
            parent=self.project,
            title='Subproject',
            is_public=True
        )
        subproject_component = NodeFactory(
            creator=self.user,
            parent=subproject,
            title='Subcomponent',
            is_public=True
        )
        res = self.app.post(
            self.project.api_url_for('register_draft_registration', draft_id=self.draft._id),
            self.valid_embargo_payload,
            content_type='application/json',
            auth=self.user.auth
        )
        self.project.reload()
        assert_equal(res.status_code, 202)
        assert_equal(res.json['urls']['registrations'], self.project.web_url_for('node_registrations'))

        # Last node directly registered from self.project
        registration = Node.find(
            Q('registered_from', 'eq', self.project)
        ).sort('-registered_date')[0]

        assert_true(registration.is_registration)
        assert_false(registration.is_public)
        assert_true(registration.is_pending_embargo_for_existing_registration)
        assert_is_not_none(registration.embargo)

        for node in registration.get_descendants_recursive():
            assert_true(node.is_registration)
            assert_false(node.is_public)

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_POST_invalid_embargo_end_date_returns_HTTPBad_Request(self, mock_enqueue):
        res = self.app.post(
            self.project.api_url_for('register_draft_registration', draft_id=self.draft._id),
            self.invalid_embargo_date_payload,
            content_type='application/json',
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 400)

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_valid_POST_embargo_adds_to_parent_projects_log(self, mock_enquque):
        initial_project_logs = len(self.project.logs)
        self.app.post(
            self.project.api_url_for('register_draft_registration', draft_id=self.draft._id),
            self.valid_embargo_payload,
            content_type='application/json',
            auth=self.user.auth
        )
        self.project.reload()
        # Logs: Created, registered, embargo initiated
        assert_equal(len(self.project.logs), initial_project_logs + 1)

    def test_embargoed_registration_can_be_made_public_by_sole_admin(self):
        # Initiate and approve embargo
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        approval_token = self.registration.embargo.approval_state[self.user._id]['approval_token']
        self.registration.embargo.approve_embargo(self.user, approval_token)
        self.registration.save()

        res = self.app.post(
            self.registration.api_url_for('project_set_privacy', permissions='public'),
            auth=self.user.auth,
        )
        assert_equal(res.status_code, 200)
        self.registration.reload()
        assert_true(self.registration.is_public)

    def test_make_embargoed_registration_by_sole_admin_makes_tree_public(self):
        # Initiate and approve embargo
        node = NodeFactory(creator=self.user)
        child = NodeFactory(parent=node, creator=self.user)
        NodeFactory(parent=child, creator=self.user)
        registration = RegistrationFactory(project=node)
        registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        approval_token = registration.embargo.approval_state[self.user._id]['approval_token']
        registration.embargo.approve_embargo(self.user, approval_token)
        registration.save()

        for node in registration.node_and_primary_descendants():
            assert_false(node.is_public)

        res = self.app.post(
            registration.api_url_for('project_set_privacy', permissions='public'),
            auth=self.user.auth,
        )
        assert_equal(res.status_code, 200)
        registration.reload()
        for node in registration.node_and_primary_descendants():
            node.reload()
            assert_true(node.is_public)

    @mock.patch('website.project.sanctions.TokenApprovableSanction.ask')
    def test_embargoed_registration_set_privacy_multiple_admins_requests_embargo_termination(self, mock_ask):
        # Initiate and approve embargo
        for i in range(3):
            c = AuthUserFactory()
            self.registration.add_contributor(c, [permissions.ADMIN], auth=Auth(self.user))
        self.registration.save()
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        for user_id, embargo_tokens in self.registration.embargo.approval_state.iteritems():
            approval_token = embargo_tokens['approval_token']
            self.registration.embargo.approve_embargo(User.load(user_id), approval_token)
        self.registration.save()

        res = self.app.post(
            self.registration.api_url_for('project_set_privacy', permissions='public'),
            auth=self.user.auth,
        )
        assert_equal(res.status_code, 200)
        for reg in self.registration.node_and_primary_descendants():
            reg.reload()
            assert_false(reg.is_public)
        assert_true(reg.embargo_termination_approval)
        assert_true(reg.embargo_termination_approval.is_pending_approval)

    @mock.patch('website.project.sanctions.TokenApprovableSanction.ask')
    def test_make_child_embargoed_registration_public_asks_all_admins_in_tree(self, mock_ask):
        # Initiate and approve embargo
        node = NodeFactory(creator=self.user)
        c1 = AuthUserFactory()
        child = NodeFactory(parent=node, creator=c1)
        c2 = AuthUserFactory()
        NodeFactory(parent=child, creator=c2)
        registration = RegistrationFactory(project=node)

        registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        for user_id, embargo_tokens in registration.embargo.approval_state.iteritems():
            approval_token = embargo_tokens['approval_token']
            registration.embargo.approve_embargo(User.load(user_id), approval_token)
        self.registration.save()

        sub_reg = registration.nodes[0].nodes[0]
        res = self.app.post(
            sub_reg.api_url_for('project_set_privacy', permissions='public'),
            auth=c2.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 200)
        sub_reg.reload()
        assert_true(sub_reg.embargo_termination_approval)
        assert_true(sub_reg.embargo_termination_approval.is_pending_approval)
        asked_admins = [(admin._id, n._id) for admin, n in mock_ask.call_args[0][0]]
        for admin, node in registration.get_admin_contributors_recursive():
            assert_in((admin._id, node._id), asked_admins)

    def test_non_contributor_GET_approval_returns_HTTPError(self):
        non_contributor = AuthUserFactory()
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        approval_token = self.registration.embargo.approval_state[self.user._id]['approval_token']
        approval_url = self.registration.web_url_for('view_project', token=approval_token)

        res = self.app.get(approval_url, auth=non_contributor.auth, expect_errors=True)
        assert_equal(http.FORBIDDEN, res.status_code)
        assert_true(self.registration.is_pending_embargo)
        assert_true(self.registration.embargo_end_date)

    def test_non_contributor_GET_disapproval_returns_HTTPError(self):
        non_contributor = AuthUserFactory()
        self.registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        rejection_token = self.registration.embargo.approval_state[self.user._id]['rejection_token']
        approval_url = self.registration.web_url_for('view_project', token=rejection_token)

        res = self.app.get(approval_url, auth=non_contributor.auth, expect_errors=True)
        assert_equal(http.FORBIDDEN, res.status_code)
        assert_true(self.registration.is_pending_embargo)
        assert_true(self.registration.embargo_end_date)
