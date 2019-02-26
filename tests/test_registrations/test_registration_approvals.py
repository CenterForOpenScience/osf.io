import datetime

import mock
from django.utils import timezone
from nose.tools import *  # noqa
from tests.base import fake, OsfTestCase
from osf_tests.factories import (
    EmbargoFactory, NodeFactory, ProjectFactory,
    RegistrationFactory, UserFactory, UnconfirmedUserFactory
)

from framework.exceptions import PermissionsError
from osf.exceptions import (
    InvalidSanctionRejectionToken, InvalidSanctionApprovalToken, NodeStateError,
)
from website import tokens
from osf.models.sanctions import (
    Sanction,
    PreregCallbackMixin,
    RegistrationApproval,
)
from framework.auth import Auth
from osf.models import Contributor, SpamStatus


DUMMY_TOKEN = tokens.encode({
    'dummy': 'token'
})


class RegistrationApprovalModelTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationApprovalModelTestCase, self).setUp()
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.registration = RegistrationFactory(project=self.project)
        self.embargo = EmbargoFactory(user=self.user)
        self.valid_embargo_end_date = timezone.now() + datetime.timedelta(days=3)

    def test__require_approval_saves_approval(self):
        initial_count = RegistrationApproval.objects.all().count()
        self.registration._initiate_approval(
            self.user
        )
        assert_equal(RegistrationApproval.objects.all().count(), initial_count + 1)

    def test__initiate_approval_does_not_create_tokens_for_unregistered_admin(self):
        unconfirmed_user = UnconfirmedUserFactory()
        Contributor.objects.create(node=self.registration, user=unconfirmed_user)
        self.registration.add_permission(unconfirmed_user, 'admin', save=True)
        assert_true(self.registration.has_permission(unconfirmed_user, 'admin'))

        approval = self.registration._initiate_approval(
            self.user
        )
        assert_true(self.user._id in approval.approval_state)
        assert_false(unconfirmed_user._id in approval.approval_state)

    def test__initiate_approval_adds_admins_on_child_nodes(self):
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

        approval = registration._initiate_approval(registration.creator)
        assert_in(project_admin._id, approval.approval_state)
        assert_in(child_admin._id, approval.approval_state)
        assert_in(grandchild_admin._id, approval.approval_state)

        assert_not_in(project_non_admin._id, approval.approval_state)
        assert_not_in(child_non_admin._id, approval.approval_state)

    def test_require_approval_from_non_admin_raises_PermissionsError(self):
        self.registration.remove_permission(self.user, 'admin')
        self.registration.save()
        self.registration.reload()
        with assert_raises(PermissionsError):
            self.registration.require_approval(self.user)

    def test_invalid_approval_token_raises_InvalidSanctionApprovalToken(self):
        self.registration.require_approval(
            self.user
        )
        self.registration.save()
        assert_true(self.registration.is_pending_registration)

        invalid_approval_token = 'not a real token'
        with assert_raises(InvalidSanctionApprovalToken):
            self.registration.registration_approval.approve(self.user, invalid_approval_token)
        assert_true(self.registration.is_pending_registration)

    def test_non_admin_approval_token_raises_PermissionsError(self):
        non_admin = UserFactory()
        self.registration.require_approval(
            self.user,
        )
        self.registration.save()
        assert_true(self.registration.is_pending_registration)

        approval_token = self.registration.registration_approval.approval_state[self.user._id]['approval_token']
        with assert_raises(PermissionsError):
            self.registration.registration_approval.approve(non_admin, approval_token)
        assert_true(self.registration.is_pending_registration)

    def test_approval_adds_to_parent_projects_log(self):
        initial_project_logs = self.registration.registered_from.logs.count()
        self.registration.require_approval(
            self.user
        )
        self.registration.save()

        approval_token = self.registration.registration_approval.approval_state[self.user._id]['approval_token']
        self.registration.registration_approval.approve(self.user, approval_token)
        # adds initiated, approved, and registered logs
        assert_equal(self.registration.registered_from.logs.count(), initial_project_logs + 3)

    def test_one_approval_with_two_admins_stays_pending(self):
        admin2 = UserFactory()
        Contributor.objects.create(node=self.registration, user=admin2)
        self.registration.add_permission(admin2, 'admin', save=True)
        self.registration.require_approval(
            self.user
        )
        self.registration.save()

        # First admin approves
        approval_token = self.registration.registration_approval.approval_state[self.user._id]['approval_token']
        self.registration.registration_approval.approve(self.user, approval_token)
        assert_true(self.registration.is_pending_registration)
        num_of_approvals = sum([val['has_approved'] for val in self.registration.registration_approval.approval_state.values()])
        assert_equal(num_of_approvals, 1)

        # Second admin approves
        approval_token = self.registration.registration_approval.approval_state[admin2._id]['approval_token']
        self.registration.registration_approval.approve(admin2, approval_token)
        assert_false(self.registration.is_pending_registration)
        num_of_approvals = sum([val['has_approved'] for val in self.registration.registration_approval.approval_state.values()])
        assert_equal(num_of_approvals, 2)

    def test_invalid_rejection_token_raises_InvalidSanctionRejectionToken(self):
        self.registration.require_approval(
            self.user
        )
        self.registration.save()
        assert_true(self.registration.is_pending_registration)
        with assert_raises(InvalidSanctionRejectionToken):
            self.registration.registration_approval.reject(self.user, fake.sentence())
        assert_true(self.registration.is_pending_registration)

    def test_non_admin_rejection_token_raises_PermissionsError(self):
        non_admin = UserFactory()
        self.registration.require_approval(
            self.user
        )
        self.registration.save()
        assert_true(self.registration.is_pending_registration)

        rejection_token = self.registration.registration_approval.approval_state[self.user._id]['rejection_token']
        with assert_raises(PermissionsError):
            self.registration.registration_approval.reject(non_admin, rejection_token)
        assert_true(self.registration.is_pending_registration)

    def test_one_disapproval_cancels_registration_approval(self):
        self.registration.require_approval(
            self.user
        )
        self.registration.save()
        assert_true(self.registration.is_pending_registration)

        rejection_token = self.registration.registration_approval.approval_state[self.user._id]['rejection_token']
        self.registration.registration_approval.reject(self.user, rejection_token)
        assert_equal(self.registration.registration_approval.state, Sanction.REJECTED)
        assert_false(self.registration.is_pending_registration)

    def test_disapproval_adds_to_parent_projects_log(self):
        initial_project_logs = self.registration.registered_from.logs.count()
        self.registration.require_approval(self.user)
        self.registration.save()

        rejection_token = self.registration.registration_approval.approval_state[self.user._id]['rejection_token']
        registered_from = self.registration.registered_from
        self.registration.registration_approval.reject(self.user, rejection_token)
        # Logs: Created, registered, embargo initiated, embargo cancelled
        assert_equal(registered_from.logs.count(), initial_project_logs + 2)

    def test_cancelling_registration_approval_deletes_parent_registration(self):
        self.registration.require_approval(
            self.user
        )
        self.registration.save()

        rejection_token = self.registration.registration_approval.approval_state[self.user._id]['rejection_token']
        self.registration.registration_approval.reject(self.user, rejection_token)
        self.registration.reload()
        assert_equal(self.registration.registration_approval.state, Sanction.REJECTED)
        assert_true(self.registration.is_deleted)

    def test_cancelling_registration_approval_deletes_component_registrations(self):
        component = NodeFactory(
            creator=self.user,
            parent=self.project,
            title='Component'
        )
        NodeFactory(
            creator=self.user,
            parent=component,
            title='Subcomponent'
        )
        project_registration = RegistrationFactory(project=self.project)
        component_registration = project_registration._nodes.first()
        subcomponent_registration = component_registration._nodes.first()
        project_registration.require_approval(
            self.user
        )
        project_registration.save()

        rejection_token = project_registration.registration_approval.approval_state[self.user._id]['rejection_token']
        project_registration.registration_approval.reject(self.user, rejection_token)
        project_registration.reload()
        component_registration.reload()
        subcomponent_registration.reload()
        assert_equal(project_registration.registration_approval.state, Sanction.REJECTED)
        assert_true(project_registration.is_deleted)
        assert_true(component_registration.is_deleted)
        assert_true(subcomponent_registration.is_deleted)

    def test_new_registration_is_pending_registration(self):
        self.registration.require_approval(
            self.user
        )
        self.registration.save()
        assert_true(self.registration.is_pending_registration)

    def test_on_complete_notify_initiator(self):
        self.registration.require_approval(
            self.user,
            notify_initiator_on_complete=True
        )
        self.registration.save()
        with mock.patch.object(PreregCallbackMixin, '_notify_initiator') as mock_notify:
            self.registration.registration_approval._on_complete(self.user)
        assert_equal(mock_notify.call_count, 1)

    def test__on_complete_makes_project_and_components_public(self):
        project_admin = UserFactory()
        child_admin = UserFactory()
        grandchild_admin = UserFactory()

        project = ProjectFactory(creator=project_admin, is_public=False)
        child = NodeFactory(creator=child_admin, parent=project, is_public=False)
        grandchild = NodeFactory(creator=grandchild_admin, parent=child, is_public=False)  # noqa

        registration = RegistrationFactory(project=project)
        with mock.patch.object(PreregCallbackMixin, '_notify_initiator'):
            registration.registration_approval._on_complete(self.user)

    def test__on_complete_raises_error_if_project_is_spam(self):
        self.registration.require_approval(
            self.user,
            notify_initiator_on_complete=True
        )
        self.registration.spam_status = SpamStatus.FLAGGED
        self.registration.save()
        with mock.patch.object(PreregCallbackMixin, '_notify_initiator') as mock_notify:
            with assert_raises(NodeStateError):
                self.registration.registration_approval._on_complete(self.user)
        assert_equal(mock_notify.call_count, 0)
