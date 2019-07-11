"""Tests related to embargoes of registrations"""
import datetime
from rest_framework import status as http_status
import json

import pytz
from django.core.exceptions import ValidationError
from django.utils import timezone

import mock
import pytest
from nose.tools import *  # noqa

from tests.base import fake, OsfTestCase
from osf_tests.factories import (
    AuthUserFactory, EmbargoFactory, NodeFactory, ProjectFactory,
    RegistrationFactory, UserFactory, UnconfirmedUserFactory, DraftRegistrationFactory,
    EmbargoTerminationApprovalFactory
)
from tests import utils

from framework.exceptions import PermissionsError, HTTPError
from framework.auth import Auth
from osf.exceptions import (
    InvalidSanctionRejectionToken, InvalidSanctionApprovalToken, NodeStateError,
)
from osf.utils import tokens
from osf.models import AbstractNode
from osf.models.sanctions import PreregCallbackMixin, Embargo
from osf.utils import permissions
from osf.models import Registration, Contributor, OSFUser, SpamStatus

DUMMY_TOKEN = tokens.encode({
    'dummy': 'token'
})


@pytest.mark.enable_bookmark_creation
class RegistrationEmbargoModelsTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationEmbargoModelsTestCase, self).setUp()
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.registration = RegistrationFactory(project=self.project)
        self.embargo = EmbargoFactory(user=self.user)
        self.valid_embargo_end_date = timezone.now() + datetime.timedelta(days=3)

    # Node#_initiate_embargo tests
    def test__initiate_embargo_saves_embargo(self):
        initial_count = Embargo.objects.all().count()
        self.registration._initiate_embargo(
            self.user,
            self.valid_embargo_end_date,
            for_existing_registration=True
        )
        assert_equal(Embargo.objects.all().count(), initial_count + 1)

    def test_state_can_be_set_to_complete(self):
        embargo = EmbargoFactory()
        embargo.state = Embargo.COMPLETED
        embargo.save()  # should pass validation
        assert_equal(embargo.state, Embargo.COMPLETED)

    def test__initiate_embargo_does_not_create_tokens_for_unregistered_admin(self):
        unconfirmed_user = UnconfirmedUserFactory()
        contrib = Contributor.objects.create(user=unconfirmed_user, node=self.registration)
        self.registration.add_permission(unconfirmed_user, permissions.ADMIN, save=True)
        assert_equal(Contributor.objects.get(node=self.registration, user=unconfirmed_user).permission, permissions.ADMIN)

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
        child.add_contributor(child_non_admin, auth=Auth(child.creator), save=True)

        grandchild = NodeFactory(creator=grandchild_admin, parent=child)  # noqa

        registration = RegistrationFactory(project=project)

        embargo = registration._initiate_embargo(
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
        initial_count = Embargo.objects.all().count()
        self.registration._initiate_embargo(
            self.user,
            self.valid_embargo_end_date,
            for_existing_registration=True,
        )
        assert_equal(Embargo.objects.all().count(), initial_count + 1)

    # Node#embargo_registration tests
    def test_embargo_from_non_admin_raises_PermissionsError(self):
        self.registration.remove_permission(self.user, permissions.ADMIN)
        self.registration.save()
        self.registration.reload()
        with assert_raises(PermissionsError):
            self.registration.embargo_registration(self.user, self.valid_embargo_end_date)

    def test_embargo_end_date_in_past_raises_ValueError(self):
        with assert_raises(ValidationError):
            self.registration.embargo_registration(
                self.user,
                datetime.datetime(1999, 1, 1, tzinfo=pytz.utc)
            )

    def test_embargo_end_date_today_raises_ValueError(self):
        with assert_raises(ValidationError):
            self.registration.embargo_registration(
                self.user,
                timezone.now()
            )

    def test_embargo_end_date_in_far_future_raises_ValidationError(self):
        with assert_raises(ValidationError):
            self.registration.embargo_registration(
                self.user,
                datetime.datetime(2099, 1, 1, tzinfo=pytz.utc)
            )

    def test_embargo_with_valid_end_date_starts_pending_embargo(self):
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

    def test_embargo_public_project_makes_private_pending_embargo(self):
        self.registration.is_public = True
        assert_true(self.registration.is_public)
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)
        assert_false(self.registration.is_public)

    # Embargo#approve_embargo tests
    def test_invalid_approval_token_raises_InvalidSanctionApprovalToken(self):
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10)
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
            timezone.now() + datetime.timedelta(days=10)
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
            timezone.now() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        approval_token = self.registration.embargo.approval_state[self.user._id]['approval_token']
        self.registration.embargo.approve_embargo(self.user, approval_token)
        assert_true(self.registration.embargo_end_date)
        assert_false(self.registration.is_pending_embargo)

    def test_approval_adds_to_parent_projects_log(self):
        initial_project_logs = self.registration.registered_from.logs.count()
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10)
        )
        self.registration.save()

        approval_token = self.registration.embargo.approval_state[self.user._id]['approval_token']
        self.registration.embargo.approve_embargo(self.user, approval_token)
        # Logs: Created, registered, embargo initiated, embargo approved
        assert_equal(self.registration.registered_from.logs.count(), initial_project_logs + 2)

    def test_one_approval_with_two_admins_stays_pending(self):
        admin2 = UserFactory()
        Contributor.objects.create(user=admin2, node=self.registration)
        self.registration.add_permission(admin2, permissions.ADMIN, save=True)
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10)
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
            timezone.now() + datetime.timedelta(days=10)
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
            timezone.now() + datetime.timedelta(days=10)
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
            timezone.now() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        rejection_token = self.registration.embargo.approval_state[self.user._id]['rejection_token']
        self.registration.embargo.disapprove_embargo(self.user, rejection_token)
        assert_equal(self.registration.embargo.state, Embargo.REJECTED)
        assert_false(self.registration.is_pending_embargo)

    def test_disapproval_adds_to_parent_projects_log(self):
        initial_project_logs = self.registration.registered_from.logs.count()
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10)
        )
        self.registration.save()

        rejection_token = self.registration.embargo.approval_state[self.user._id]['rejection_token']
        registered_from = self.registration.registered_from
        self.registration.embargo.disapprove_embargo(self.user, rejection_token)
        # Logs: Created, registered, embargo initiated, embargo cancelled
        assert_equal(registered_from.logs.count(), initial_project_logs + 2)

    def test_cancelling_embargo_deletes_parent_registration(self):
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10)
        )
        self.registration.save()

        rejection_token = self.registration.embargo.approval_state[self.user._id]['rejection_token']
        self.registration.embargo.disapprove_embargo(self.user, rejection_token)
        self.registration.reload()
        assert_equal(self.registration.embargo.state, Embargo.REJECTED)
        assert_true(self.registration.is_deleted)

    def test_cancelling_embargo_deletes_component_registrations(self):
        component = NodeFactory(
            creator=self.user,
            parent=self.project,
            title='Component'
        )
        NodeFactory(  # subcomponent
            creator=self.user,
            parent=component,
            title='Subcomponent'
        )
        project_registration = RegistrationFactory(project=self.project)
        component_registration = project_registration._nodes.first()
        subcomponent_registration = component_registration._nodes.first()
        project_registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10)
        )
        project_registration.save()

        rejection_token = project_registration.embargo.approval_state[self.user._id]['rejection_token']
        project_registration.embargo.disapprove_embargo(self.user, rejection_token)
        assert_equal(project_registration.embargo.state, Embargo.REJECTED)
        project_registration.reload()
        assert_true(project_registration.is_deleted)
        component_registration.reload()
        assert_true(component_registration.is_deleted)
        subcomponent_registration.reload()
        assert_true(subcomponent_registration.is_deleted)

    def test_cancelling_embargo_for_existing_registration_does_not_delete_registration(self):
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10),
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
        NodeFactory(  # subcomponent
            creator=self.user,
            parent=component,
            title='Subcomponent'
        )
        project_registration = RegistrationFactory(project=self.project)
        component_registration = project_registration._nodes.first()
        subcomponent_registration = component_registration._nodes.first()
        project_registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10),
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
            timezone.now() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo_for_existing_registration)

    def test_existing_registration_is_not_pending_registration(self):
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10),
            for_existing_registration=True
        )
        self.registration.save()
        assert_false(self.registration.is_pending_embargo_for_existing_registration)

    def test_on_complete_notify_initiator(self):
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10),
            notify_initiator_on_complete=True
        )
        self.registration.save()
        with mock.patch.object(PreregCallbackMixin, '_notify_initiator') as mock_notify:
            self.registration.embargo._on_complete(self.user)
        assert_equal(mock_notify.call_count, 1)

    def test_on_complete_raises_error_if_registration_is_spam(self):
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10),
            notify_initiator_on_complete=True
        )
        self.registration.spam_status = SpamStatus.FLAGGED
        self.registration.save()
        with mock.patch.object(PreregCallbackMixin, '_notify_initiator') as mock_notify:
            with assert_raises(NodeStateError):
                self.registration.embargo._on_complete(self.user)
        assert_equal(mock_notify.call_count, 0)

    # Regression for OSF-8840
    def test_public_embargo_cannot_be_deleted_with_initial_token(self):
        embargo_termination_approval = EmbargoTerminationApprovalFactory()
        registration = Registration.objects.get(embargo_termination_approval=embargo_termination_approval)
        user = registration.contributors.first()

        registration.terminate_embargo(Auth(user))

        rejection_token = registration.embargo.approval_state[user._id]['rejection_token']
        with assert_raises(HTTPError) as e:
            registration.embargo.disapprove_embargo(user, rejection_token)

        registration.refresh_from_db()
        assert registration.is_deleted is False


@pytest.mark.enable_bookmark_creation
class RegistrationWithChildNodesEmbargoModelTestCase(OsfTestCase):

    def setUp(self):
        super(RegistrationWithChildNodesEmbargoModelTestCase, self).setUp()
        self.user = AuthUserFactory()
        self.auth = self.user.auth
        self.valid_embargo_end_date = timezone.now() + datetime.timedelta(days=3)
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
            node.reload()
            assert_false(node.is_pending_embargo)
            assert_false(node.embargo_end_date)


@pytest.mark.enable_bookmark_creation
class LegacyRegistrationEmbargoApprovalDisapprovalViewsTestCase(OsfTestCase):
    """
    TODO: Remove this set of tests when process_token_or_pass decorator taken
    off the view_project view
    """
    def setUp(self):
        super(LegacyRegistrationEmbargoApprovalDisapprovalViewsTestCase, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.registration = RegistrationFactory(creator=self.user, project=self.project)

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
            timezone.now() + datetime.timedelta(days=10)
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
        Contributor.objects.create(user=admin2, node=self.registration)
        self.registration.add_permission(admin2, permissions.ADMIN, save=True)
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10)
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
        Contributor.objects.create(user=admin2, node=self.registration)
        self.registration.add_permission(admin2, permissions.ADMIN, save=True)
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10)
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
            timezone.now() + datetime.timedelta(days=10)
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
            timezone.now() + datetime.timedelta(days=10)
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
        Contributor.objects.create(user=admin2, node=self.registration)
        self.registration.add_permission(admin2, permissions.ADMIN, save=True)
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10)
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
            timezone.now() + datetime.timedelta(days=10)
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
            timezone.now() + datetime.timedelta(days=10),
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

    def test_GET_from_unauthorized_user_with_registration_token(self):
        unauthorized_user = AuthUserFactory()

        self.registration.require_approval(self.user)
        self.registration.save()

        app_token = self.registration.registration_approval.approval_state[self.user._id]['approval_token']
        rej_token = self.registration.registration_approval.approval_state[self.user._id]['rejection_token']

        # Test unauth user cannot approve
        res = self.app.get(
            # approval token goes through registration
            self.registration.web_url_for('view_project', token=app_token),
            auth=unauthorized_user.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 401)

        # Test unauth user cannot reject
        res = self.app.get(
            # rejection token goes through registration parent
            self.project.web_url_for('view_project', token=rej_token),
            auth=unauthorized_user.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 401)

        # Delete Node and try again
        self.project.is_deleted = True
        self.project.save()

        # Test unauth user cannot approve deleted node
        res = self.app.get(
            self.registration.web_url_for('view_project', token=app_token),
            auth=unauthorized_user.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 401)

        # Test unauth user cannot reject
        res = self.app.get(
            self.project.web_url_for('view_project', token=rej_token),
            auth=unauthorized_user.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 401)

        # Test auth user can approve registration with deleted parent
        res = self.app.get(
            self.registration.web_url_for('view_project', token=app_token),
            auth=self.user.auth,
        )
        assert_equal(res.status_code, 200)

    def test_GET_from_authorized_user_with_registration_app_token(self):
        self.registration.require_approval(self.user)
        self.registration.save()
        app_token = self.registration.registration_approval.approval_state[self.user._id]['approval_token']

        res = self.app.get(
            self.registration.web_url_for('view_project', token=app_token),
            auth=self.user.auth,
        )
        assert_equal(res.status_code, 200)

    def test_GET_from_authorized_user_with_registration_rej_token(self):
        self.registration.require_approval(self.user)
        self.registration.save()
        rej_token = self.registration.registration_approval.approval_state[self.user._id]['rejection_token']

        res = self.app.get(
            self.project.web_url_for('view_project', token=rej_token),
            auth=self.user.auth,
        )
        assert_equal(res.status_code, 200)

    def test_GET_from_authorized_user_with_registration_rej_token_deleted_node(self):
        self.registration.require_approval(self.user)
        self.registration.save()
        rej_token = self.registration.registration_approval.approval_state[self.user._id]['rejection_token']

        self.project.is_deleted = True
        self.project.save()

        res = self.app.get(
            self.project.web_url_for('view_project', token=rej_token),
            auth=self.user.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 410)
        res = self.app.get(
            self.registration.web_url_for('view_project'),
            auth=self.user.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 410)


@pytest.mark.enable_bookmark_creation
class RegistrationEmbargoApprovalDisapprovalViewsTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationEmbargoApprovalDisapprovalViewsTestCase, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.registration = RegistrationFactory(creator=self.user, project=self.project)

    def test_GET_approve_registration_without_embargo_raises_HTTPBad_Request(self):
        assert_false(self.registration.is_pending_embargo)
        res = self.app.get(
            self.registration.web_url_for('token_action', token=DUMMY_TOKEN),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_GET_approve_with_invalid_token_returns_HTTPBad_Request(self):
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        res = self.app.get(
            self.registration.web_url_for('token_action', token=DUMMY_TOKEN),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_GET_approve_with_wrong_token_returns_HTTPBad_Request(self):
        admin2 = UserFactory()
        Contributor.objects.create(user=admin2, node=self.registration)
        self.registration.add_permission(admin2, permissions.ADMIN, save=True)
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        wrong_approval_token = self.registration.embargo.approval_state[admin2._id]['approval_token']
        res = self.app.get(
            self.registration.web_url_for('token_action', token=wrong_approval_token),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_GET_approve_with_wrong_admins_token_returns_HTTPBad_Request(self):
        admin2 = UserFactory()
        Contributor.objects.create(user=admin2, node=self.registration)
        self.registration.add_permission(admin2, permissions.ADMIN, save=True)
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        wrong_approval_token = self.registration.embargo.approval_state[admin2._id]['approval_token']
        res = self.app.get(
            self.registration.web_url_for('token_action', token=wrong_approval_token),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_true(self.registration.is_pending_embargo)
        assert_equal(res.status_code, 400)

    @mock.patch('flask.redirect')
    def test_GET_approve_with_valid_token_redirects(self, mock_redirect):
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        approval_token = self.registration.embargo.approval_state[self.user._id]['approval_token']
        self.app.get(
            self.registration.web_url_for('token_action', token=approval_token),
            auth=self.user.auth,
        )
        self.registration.embargo.reload()
        assert_true(self.registration.embargo_end_date)
        assert_false(self.registration.is_pending_embargo)
        assert_true(mock_redirect.called_with(self.registration.web_url_for('view_project')))

    def test_GET_disapprove_registration_without_embargo_HTTPBad_Request(self):
        assert_false(self.registration.is_pending_embargo)
        res = self.app.get(
            self.registration.web_url_for('token_action', token=DUMMY_TOKEN),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_GET_disapprove_with_invalid_token_returns_HTTPBad_Request(self):
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        res = self.app.get(
            self.registration.web_url_for('token_action', token=DUMMY_TOKEN),
            auth=self.user.auth,
            expect_errors=True
        )
        self.registration.embargo.reload()
        assert_true(self.registration.is_pending_embargo)
        assert_equal(res.status_code, 400)

    def test_GET_disapprove_with_wrong_admins_token_returns_HTTPBad_Request(self):
        admin2 = UserFactory()
        Contributor.objects.create(user=admin2, node=self.registration)
        self.registration.add_permission(admin2, permissions.ADMIN, save=True)
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        wrong_rejection_token = self.registration.embargo.approval_state[admin2._id]['rejection_token']
        res = self.app.get(
            self.registration.web_url_for('token_action', token=wrong_rejection_token),
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
            timezone.now() + datetime.timedelta(days=10)
        )
        registration.save()
        assert_true(registration.is_pending_embargo)

        rejection_token = registration.embargo.approval_state[self.user._id]['rejection_token']

        res = self.app.get(
            registration.registered_from.web_url_for('token_action', token=rejection_token),
            auth=self.user.auth,
        )
        registration.embargo.reload()
        assert_equal(registration.embargo.state, Embargo.REJECTED)
        assert_false(registration.is_pending_embargo)
        assert_equal(res.status_code, 302)
        assert_equal(project.web_url_for('token_action'), res.request.path)

    def test_GET_disapprove_for_existing_registration_returns_200(self):
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10),
            for_existing_registration=True
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        rejection_token = self.registration.embargo.approval_state[self.user._id]['rejection_token']
        res = self.app.get(
            self.registration.web_url_for('token_action', token=rejection_token),
            auth=self.user.auth,
        )
        self.registration.embargo.reload()
        assert_equal(self.registration.embargo.state, Embargo.REJECTED)
        assert_false(self.registration.is_pending_embargo)
        assert_equal(res.status_code, 302)
        assert_equal(res.request.path, self.registration.web_url_for('token_action'))

    def test_GET_from_unauthorized_user_with_registration_token(self):
        unauthorized_user = AuthUserFactory()

        self.registration.require_approval(self.user)
        self.registration.save()

        app_token = self.registration.registration_approval.approval_state[self.user._id]['approval_token']
        rej_token = self.registration.registration_approval.approval_state[self.user._id]['rejection_token']

        # Test unauth user cannot approve
        res = self.app.get(
            # approval token goes through registration
            self.registration.web_url_for('token_action', token=app_token),
            auth=unauthorized_user.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 401)

        # Test unauth user cannot reject
        res = self.app.get(
            # rejection token goes through registration parent
            self.project.web_url_for('token_action', token=rej_token),
            auth=unauthorized_user.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 401)

        # Delete Node and try again
        self.project.is_deleted = True
        self.project.save()

        # Test unauth user cannot approve deleted node
        res = self.app.get(
            self.registration.web_url_for('token_action', token=app_token),
            auth=unauthorized_user.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 401)

        # Test unauth user cannot reject
        res = self.app.get(
            self.project.web_url_for('token_action', token=rej_token),
            auth=unauthorized_user.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 401)

        # Test auth user can approve registration with deleted parent
        res = self.app.get(
            self.registration.web_url_for('token_action', token=app_token),
            auth=self.user.auth,
        )
        assert_equal(res.status_code, 302)

    def test_GET_from_authorized_user_with_registration_app_token(self):
        self.registration.require_approval(self.user)
        self.registration.save()
        app_token = self.registration.registration_approval.approval_state[self.user._id]['approval_token']

        res = self.app.get(
            self.registration.web_url_for('token_action', token=app_token),
            auth=self.user.auth,
        )
        assert_equal(res.status_code, 302)

    def test_GET_from_authorized_user_with_registration_rej_token(self):
        self.registration.require_approval(self.user)
        self.registration.save()
        rej_token = self.registration.registration_approval.approval_state[self.user._id]['rejection_token']

        res = self.app.get(
            self.project.web_url_for('token_action', token=rej_token),
            auth=self.user.auth,
        )
        assert_equal(res.status_code, 302)

    def test_GET_from_authorized_user_with_registration_rej_token_deleted_node(self):
        self.registration.require_approval(self.user)
        self.registration.save()
        rej_token = self.registration.registration_approval.approval_state[self.user._id]['rejection_token']

        self.project.is_deleted = True
        self.project.save()

        res = self.app.get(
            self.project.web_url_for('token_action', token=rej_token),
            auth=self.user.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 410)
        res = self.app.get(
            self.registration.web_url_for('token_action'),
            auth=self.user.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, 410)


@pytest.mark.enable_bookmark_creation
class RegistrationEmbargoViewsTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationEmbargoViewsTestCase, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.draft = DraftRegistrationFactory(branched_from=self.project)
        self.registration = RegistrationFactory(project=self.project, creator=self.user)

        current_month = timezone.now().strftime('%B')
        current_year = timezone.now().strftime('%Y')

        self.valid_make_public_payload = json.dumps({
            'data': {
                'attributes': {
                    u'registration_choice': 'immediate',
                },
                'type': 'registrations',
            }
        })
        valid_date = timezone.now() + datetime.timedelta(days=180)
        self.valid_embargo_payload = json.dumps({
            'data': {
                'attributes': {
                    u'lift_embargo': unicode(valid_date.strftime('%a, %d, %B %Y %H:%M:%S')) + u' GMT',
                    u'registration_choice': 'embargo',
                },
                'type': 'registrations',
            },
        })
        self.invalid_embargo_date_payload = json.dumps({
            'data': {
                'attributes': {
                    u'lift_embargo': u'Thu, 01 {month} {year} 05:00:00 GMT'.format(
                        month=current_month,
                        year=str(int(current_year) - 1)
                    ),
                    u'registration_choice': 'embargo',
                },
                'type': 'registrations',
            }
        })


    @mock.patch('osf.models.sanctions.TokenApprovableSanction.ask')
    def test_embargoed_registration_set_privacy_requests_embargo_termination(self, mock_ask):
        # Initiate and approve embargo
        for i in range(3):
            c = AuthUserFactory()
            self.registration.add_contributor(c, permissions.ADMIN, auth=Auth(self.user))
        self.registration.save()
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10)
        )
        for user_id, embargo_tokens in self.registration.embargo.approval_state.items():
            approval_token = embargo_tokens['approval_token']
            self.registration.embargo.approve_embargo(OSFUser.load(user_id), approval_token)
        self.registration.save()

        self.registration.set_privacy('public', Auth(self.registration.creator))
        for reg in self.registration.node_and_primary_descendants():
            reg.reload()
            assert_false(reg.is_public)
        assert_true(reg.embargo_termination_approval)
        assert_true(reg.embargo_termination_approval.is_pending_approval)

    def test_cannot_request_termination_on_component_of_embargo(self):
        node = ProjectFactory()
        ProjectFactory(parent=node, creator=node.creator)  # child project

        with utils.mock_archive(node, embargo=True, autocomplete=True, autoapprove=True) as reg:
            with assert_raises(NodeStateError):
                reg._nodes.first().request_embargo_termination(Auth(node.creator))

    @mock.patch('website.mails.send_mail')
    def test_embargoed_registration_set_privacy_sends_mail(self, mock_send_mail):
        """
        Integration test for https://github.com/CenterForOpenScience/osf.io/pull/5294#issuecomment-212613668
        """
        # Initiate and approve embargo
        for i in range(3):
            c = AuthUserFactory()
            self.registration.add_contributor(c, permissions.ADMIN, auth=Auth(self.user))
        self.registration.save()
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10)
        )
        for user_id, embargo_tokens in self.registration.embargo.approval_state.items():
            approval_token = embargo_tokens['approval_token']
            self.registration.embargo.approve_embargo(OSFUser.load(user_id), approval_token)
        self.registration.save()

        self.registration.set_privacy('public', Auth(self.registration.creator))
        admin_contributors = []
        for contributor in self.registration.contributors:
            if Contributor.objects.get(user_id=contributor.id, node_id=self.registration.id).permission == permissions.ADMIN:
                admin_contributors.append(contributor)
        for admin in admin_contributors:
            assert_true(any([each[0][0] == admin.username for each in mock_send_mail.call_args_list]))

    @mock.patch('osf.models.sanctions.TokenApprovableSanction.ask')
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
            timezone.now() + datetime.timedelta(days=10)
        )
        for user_id, embargo_tokens in registration.embargo.approval_state.items():
            approval_token = embargo_tokens['approval_token']
            registration.embargo.approve_embargo(OSFUser.load(user_id), approval_token)
        self.registration.save()

        registration.set_privacy('public', Auth(self.registration.creator))
        asked_admins = [(admin._id, n._id) for admin, n in mock_ask.call_args[0][0]]
        for admin, node in registration.get_admin_contributors_recursive():
            assert_in((admin._id, node._id), asked_admins)

    def test_non_contributor_GET_approval_returns_HTTPError(self):
        non_contributor = AuthUserFactory()
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        approval_token = self.registration.embargo.approval_state[self.user._id]['approval_token']
        approval_url = self.registration.web_url_for('token_action', token=approval_token)

        res = self.app.get(approval_url, auth=non_contributor.auth, expect_errors=True)
        self.registration.reload()
        assert_equal(http_status.HTTP_401_UNAUTHORIZED, res.status_code)
        assert_true(self.registration.is_pending_embargo)
        assert_equal(self.registration.embargo.state, Embargo.UNAPPROVED)

    def test_non_contributor_GET_disapproval_returns_HTTPError(self):
        non_contributor = AuthUserFactory()
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10)
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        rejection_token = self.registration.embargo.approval_state[self.user._id]['rejection_token']
        approval_url = self.registration.web_url_for('token_action', token=rejection_token)

        res = self.app.get(approval_url, auth=non_contributor.auth, expect_errors=True)
        assert_equal(http_status.HTTP_401_UNAUTHORIZED, res.status_code)
        assert_true(self.registration.is_pending_embargo)
        assert_equal(self.registration.embargo.state, Embargo.UNAPPROVED)
