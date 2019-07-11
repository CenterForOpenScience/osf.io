"""Tests related to retraction of public registrations"""

import datetime
from rest_framework import status as http_status

import mock
import pytest
from django.utils import timezone
from django.db import DataError
from nose.tools import *  # noqa

from framework.auth import Auth
from framework.exceptions import PermissionsError
from tests.base import fake, OsfTestCase
from osf_tests.factories import (
    AuthUserFactory, NodeFactory, ProjectFactory,
    RegistrationFactory, UserFactory, UnconfirmedUserFactory,
    UnregUserFactory, OSFGroupFactory
)
from osf.utils import tokens
from osf.exceptions import (
    InvalidSanctionApprovalToken, InvalidSanctionRejectionToken,
    NodeStateError,
)
from osf.models import Contributor, Retraction
from osf.utils import permissions


@pytest.mark.enable_bookmark_creation
class RegistrationRetractionModelsTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationRetractionModelsTestCase, self).setUp()

        self.user = UserFactory()
        self.registration = RegistrationFactory(creator=self.user, is_public=True)
        self.valid_justification = fake.sentence()
        self.invalid_justification = fake.text(max_nb_chars=3000)

    def test_set_public_registration_to_private_raises_NodeStateException(self):
        self.registration.save()
        with assert_raises(NodeStateError):
            self.registration.set_privacy('private')
        self.registration.reload()

        assert_true(self.registration.is_public)

    def test_initiate_retraction_saves_retraction(self):
        initial_count = Retraction.objects.all().count()
        self.registration._initiate_retraction(self.user)
        assert_equal(Retraction.objects.all().count(), initial_count + 1)

    def test__initiate_retraction_does_not_create_tokens_for_unregistered_admin(self):
        unconfirmed_user = UnconfirmedUserFactory()
        Contributor.objects.create(node=self.registration, user=unconfirmed_user)
        self.registration.add_permission(unconfirmed_user, permissions.ADMIN, save=True)
        assert_equal(Contributor.objects.get(node=self.registration, user=unconfirmed_user).permission, permissions.ADMIN)

        retraction = self.registration._initiate_retraction(self.user)
        assert_true(self.user._id in retraction.approval_state)
        assert_false(unconfirmed_user._id in retraction.approval_state)

    def test__initiate_retraction_adds_admins_on_child_nodes(self):
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

        retraction = registration._initiate_retraction(registration.creator)
        assert_in(project_admin._id, retraction.approval_state)
        assert_in(child_admin._id, retraction.approval_state)
        assert_in(grandchild_admin._id, retraction.approval_state)

        assert_not_in(project_non_admin._id, retraction.approval_state)
        assert_not_in(child_non_admin._id, retraction.approval_state)

    # Backref tests
    def test_retraction_initiator_has_backref(self):
        self.registration.retract_registration(self.user, self.valid_justification)
        self.registration.save()
        self.registration.reload()
        assert_equal(Retraction.objects.filter(initiated_by=self.user).count(), 1)

    # Node#retract_registration tests
    def test_pending_retract(self):
        self.registration.retract_registration(self.user, self.valid_justification)
        self.registration.save()
        self.registration.reload()

        assert_false(self.registration.is_retracted)
        assert_equal(self.registration.retraction.state, Retraction.UNAPPROVED)
        assert_equal(self.registration.retraction.justification, self.valid_justification)
        assert_equal(self.registration.retraction.initiated_by, self.user)
        assert_equal(
            self.registration.retraction.initiation_date.date(),
            timezone.now().date()
        )

    def test_retract_component_raises_NodeStateError(self):
        project = ProjectFactory(is_public=True, creator=self.user)
        NodeFactory(is_public=True, creator=self.user, parent=project)
        registration = RegistrationFactory(is_public=True, project=project)

        with assert_raises(NodeStateError):
            registration._nodes.first().retract_registration(self.user, self.valid_justification)

    def test_long_justification_raises_ValidationValueError(self):
        with assert_raises(DataError):
            self.registration.retract_registration(self.user, self.invalid_justification)
            self.registration.save()
        assert_is_none(self.registration.retraction)

    def test_retract_private_registration_raises_NodeStateError(self):
        self.registration.is_public = False
        with assert_raises(NodeStateError):
            self.registration.retract_registration(self.user, self.valid_justification)
            self.registration.save()
        self.registration.reload()
        assert_is_none(self.registration.retraction)

    def test_retraction_of_registration_pending_embargo_cancels_embargo(self):
        self.registration.embargo_registration(
            self.user,
            (timezone.now() + datetime.timedelta(days=10)),
            for_existing_registration=True
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        self.registration.retract_registration(self.user)
        self.registration.save()
        assert_true(self.registration.is_pending_retraction)

        approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        self.registration.retraction.approve_retraction(self.user, approval_token)
        assert_false(self.registration.is_pending_retraction)
        assert_true(self.registration.is_retracted)
        self.registration.embargo.reload()
        assert_false(self.registration.is_pending_embargo)
        assert_true(self.registration.embargo.is_rejected)

    def test_retraction_of_registration_in_active_embargo_cancels_embargo(self):
        self.registration.embargo_registration(
            self.user,
            (timezone.now() + datetime.timedelta(days=10)),
            for_existing_registration=True
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        embargo_approval_token = self.registration.embargo.approval_state[self.user._id]['approval_token']
        self.registration.embargo.approve_embargo(self.user, embargo_approval_token)
        assert_false(self.registration.is_pending_embargo)
        assert_true(self.registration.embargo_end_date)

        self.registration.retract_registration(self.user)
        self.registration.save()
        assert_true(self.registration.is_pending_retraction)

        retraction_approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        self.registration.retraction.approve_retraction(self.user, retraction_approval_token)
        assert_false(self.registration.is_pending_retraction)
        assert_true(self.registration.is_retracted)
        self.registration.embargo.reload()
        assert_false(self.registration.is_pending_embargo)
        assert_true(self.registration.embargo.is_rejected)

    # Retraction#approve_retraction_tests
    def test_invalid_approval_token_raises_InvalidSanctionApprovalToken(self):
        self.registration.retract_registration(self.user)
        self.registration.save()
        assert_true(self.registration.is_pending_retraction)

        with assert_raises(InvalidSanctionApprovalToken):
            self.registration.retraction.approve_retraction(self.user, fake.sentence())
        assert_true(self.registration.is_pending_retraction)
        assert_false(self.registration.is_retracted)

    def test_non_admin_approval_token_raises_PermissionsError(self):
        non_admin = UserFactory()
        self.registration.retract_registration(self.user)
        self.registration.save()
        assert_true(self.registration.is_pending_retraction)

        approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        with assert_raises(PermissionsError):
            self.registration.retraction.approve_retraction(non_admin, approval_token)
        assert_true(self.registration.is_pending_retraction)
        assert_false(self.registration.is_retracted)

        # group admin on node cannot retract registration
        group_mem = AuthUserFactory()
        group = OSFGroupFactory(creator=group_mem)
        self.registration.registered_from.add_osf_group(group, permissions.ADMIN)
        with assert_raises(PermissionsError):
            self.registration.retraction.approve_retraction(group_mem, approval_token)
        assert_true(self.registration.is_pending_retraction)
        assert_false(self.registration.is_retracted)

    def test_one_approval_with_one_admin_retracts(self):
        self.registration.retract_registration(self.user)
        self.registration.save()

        approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        assert_true(self.registration.is_pending_retraction)
        self.registration.retraction.approve_retraction(self.user, approval_token)
        assert_true(self.registration.is_retracted)
        num_of_approvals = sum([val['has_approved'] for val in self.registration.retraction.approval_state.values()])
        assert_equal(num_of_approvals, 1)

    def test_approval_adds_to_parent_projects_log(self):
        initial_project_logs = self.registration.registered_from.logs.count()
        self.registration.retract_registration(self.user)
        self.registration.save()

        approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        self.registration.retraction.approve_retraction(self.user, approval_token)
        # Logs: Created, registered, retraction initiated, retraction approved
        assert_equal(self.registration.registered_from.logs.count(), initial_project_logs + 2)

    def test_retraction_of_registration_pending_embargo_cancels_embargo_public(self):
        self.registration.is_public = True
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10),
            for_existing_registration=True
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        self.registration.retract_registration(self.user)
        self.registration.save()
        assert_true(self.registration.is_pending_retraction)

        approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        self.registration.retraction.approve_retraction(self.user, approval_token)
        assert_false(self.registration.is_pending_retraction)
        assert_true(self.registration.is_retracted)
        self.registration.embargo.reload()
        assert_false(self.registration.is_pending_embargo)
        assert_true(self.registration.embargo.is_rejected)

    def test_approval_of_registration_with_embargo_adds_to_parent_projects_log(self):
        initial_project_logs = self.registration.registered_from.logs.count()
        self.registration.is_public = True
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10),
            for_existing_registration=True
        )
        self.registration.save()

        self.registration.retract_registration(self.user)
        self.registration.save()

        approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        self.registration.retraction.approve_retraction(self.user, approval_token)
        # Logs: Created, registered, embargo initiated, retraction initiated, retraction approved, embargo cancelled
        assert_equal(self.registration.registered_from.logs.count(), initial_project_logs + 4)

    def test_retraction_of_public_registration_in_active_embargo_cancels_embargo(self):
        self.registration.is_public = True
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10),
            for_existing_registration=True
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        embargo_approval_token = self.registration.embargo.approval_state[self.user._id]['approval_token']
        self.registration.embargo.approve_embargo(self.user, embargo_approval_token)
        assert_false(self.registration.is_pending_embargo)
        assert_true(self.registration.embargo_end_date)

        self.registration.retract_registration(self.user)
        self.registration.save()
        assert_true(self.registration.is_pending_retraction)

        retraction_approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        self.registration.retraction.approve_retraction(self.user, retraction_approval_token)
        assert_false(self.registration.is_pending_retraction)
        assert_true(self.registration.is_retracted)
        self.registration.embargo.reload()
        assert_false(self.registration.is_pending_embargo)
        assert_true(self.registration.embargo.is_rejected)

    def test_two_approvals_with_two_admins_retracts(self):
        self.admin2 = UserFactory()
        Contributor.objects.create(node=self.registration, user=self.admin2)
        self.registration.add_permission(self.admin2, permissions.ADMIN, save=True)
        self.registration.retract_registration(self.user)
        self.registration.save()
        self.registration.reload()

        # First admin approves
        approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        self.registration.retraction.approve_retraction(self.user, approval_token)
        assert_true(self.registration.is_pending_retraction)
        num_of_approvals = sum([val['has_approved'] for val in self.registration.retraction.approval_state.values()])
        assert_equal(num_of_approvals, 1)

        # Second admin approves
        approval_token = self.registration.retraction.approval_state[self.admin2._id]['approval_token']
        self.registration.retraction.approve_retraction(self.admin2, approval_token)
        num_of_approvals = sum([val['has_approved'] for val in self.registration.retraction.approval_state.values()])
        assert_equal(num_of_approvals, 2)
        assert_true(self.registration.is_retracted)

    def test_one_approval_with_two_admins_stays_pending(self):
        self.admin2 = UserFactory()
        Contributor.objects.create(node=self.registration, user=self.admin2)
        self.registration.add_permission(self.admin2, permissions.ADMIN, save=True)

        self.registration.retract_registration(self.user)
        self.registration.save()
        self.registration.reload()

        approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        assert_equal(self.registration.retraction.state, Retraction.UNAPPROVED)
        self.registration.retraction.approve_retraction(self.user, approval_token)
        assert_true(self.registration.is_pending_retraction)
        num_of_approvals = sum([val['has_approved'] for val in self.registration.retraction.approval_state.values()])
        assert_equal(num_of_approvals, 1)

    # Retraction#disapprove_retraction tests
    def test_invalid_rejection_token_raises_InvalidSanctionRejectionToken(self):
        self.registration.retract_registration(self.user)
        self.registration.save()
        assert_true(self.registration.is_pending_retraction)

        with assert_raises(InvalidSanctionRejectionToken):
            self.registration.retraction.disapprove_retraction(self.user, fake.sentence())
        assert_true(self.registration.is_pending_retraction)
        assert_false(self.registration.is_retracted)

    def test_non_admin_rejection_token_raises_PermissionsError(self):
        non_admin = UserFactory()
        self.registration.retract_registration(self.user)
        self.registration.save()
        assert_true(self.registration.is_pending_retraction)

        rejection_token = self.registration.retraction.approval_state[self.user._id]['rejection_token']
        with assert_raises(PermissionsError):
            self.registration.retraction.disapprove_retraction(non_admin, rejection_token)
        assert_true(self.registration.is_pending_retraction)
        assert_false(self.registration.is_retracted)

    def test_one_disapproval_cancels_retraction(self):
        self.registration.retract_registration(self.user)
        self.registration.save()
        self.registration.reload()

        rejection_token = self.registration.retraction.approval_state[self.user._id]['rejection_token']
        assert_equal(self.registration.retraction.state, Retraction.UNAPPROVED)
        self.registration.retraction.disapprove_retraction(self.user, rejection_token)
        assert_true(self.registration.retraction.is_rejected)

    def test_disapproval_adds_to_parent_projects_log(self):
        initial_project_logs = self.registration.registered_from.logs.count()
        self.registration.retract_registration(self.user)
        self.registration.save()
        self.registration.reload()

        rejection_token = self.registration.retraction.approval_state[self.user._id]['rejection_token']
        self.registration.retraction.disapprove_retraction(self.user, rejection_token)
        # Logs: Created, registered, retraction initiated, retraction cancelled
        assert_equal(self.registration.registered_from.logs.count(), initial_project_logs + 2)

    def test__on_complete_makes_project_and_components_public(self):
        project_admin = UserFactory()
        child_admin = UserFactory()
        grandchild_admin = UserFactory()

        project = ProjectFactory(creator=project_admin, is_public=False)
        child = NodeFactory(creator=child_admin, parent=project, is_public=False)
        grandchild = NodeFactory(creator=grandchild_admin, parent=child, is_public=False)  # noqa

        registration = RegistrationFactory(project=project)
        registration._initiate_retraction(self.user)
        registration.retraction._on_complete(self.user)
        for each in registration.node_and_primary_descendants():
            each.reload()
            assert_true(each.is_public)

    # Retraction property tests
    def test_new_retraction_is_pending_retraction(self):
        self.registration.retract_registration(self.user)
        assert_true(self.registration.is_pending_retraction)
        assert_false(self.registration.is_retracted)


@pytest.mark.enable_bookmark_creation
class RegistrationWithChildNodesRetractionModelTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationWithChildNodesRetractionModelTestCase, self).setUp()

        self.user = AuthUserFactory()
        self.auth = self.user.auth
        self.project = ProjectFactory(is_public=True, creator=self.user)
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
        self.registration = RegistrationFactory(project=self.project, is_public=True)
        # Reload the registration; else tests won't catch failures to svae
        self.registration.reload()

    @mock.patch('website.project.tasks.format_node')
    @mock.patch('website.project.tasks.format_registration')
    @mock.patch('website.project.tasks.settings.SHARE_URL', 'ima_real_website')
    @mock.patch('website.project.tasks.settings.SHARE_API_TOKEN', 'totaly_real_token')
    @mock.patch('website.project.tasks.send_share_node_data')
    def test_approval_retracts_descendant_nodes(self, mock_update_share, mock_format_registration, mock_format_node):
        # Initiate retraction for parent registration
        self.registration.retract_registration(self.user)
        self.registration.save()
        assert_true(self.registration.is_pending_retraction)

        # Ensure descendant nodes are pending registration
        descendants = self.registration.get_descendants_recursive()
        for node in descendants:
            node.save()
            assert_true(node.is_pending_retraction)

        # Approve parent registration's retraction
        approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        self.registration.retraction.approve_retraction(self.user, approval_token)
        assert_true(self.registration.is_retracted)

        # Ensure descendant nodes are retracted
        descendants = self.registration.get_descendants_recursive()
        for node in descendants:
            assert_true(node.is_retracted)

        assert mock_update_share.called
        assert mock_format_registration.called
        assert not mock_format_node.called

    def test_disapproval_cancels_retraction_on_descendant_nodes(self):
        # Initiate retraction for parent registration
        self.registration.retract_registration(self.user)
        self.registration.save()
        assert_true(self.registration.is_pending_retraction)

        # Ensure descendant nodes are pending registration
        descendants = self.registration.get_descendants_recursive()
        for node in descendants:
            node.save()
            assert_true(node.is_pending_retraction)

        # Disapprove parent registration's retraction
        rejection_token = self.registration.retraction.approval_state[self.user._id]['rejection_token']
        self.registration.retraction.disapprove_retraction(self.user, rejection_token)
        assert_false(self.registration.is_pending_retraction)
        assert_false(self.registration.is_retracted)
        assert_true(self.registration.retraction.is_rejected)

        # Ensure descendant nodes' retractions are cancelled
        descendants = self.registration.get_descendants_recursive()
        for node in descendants:
            assert_false(node.is_pending_retraction)
            assert_false(node.is_retracted)

    @mock.patch('website.project.tasks.settings.SHARE_URL', 'ima_real_website')
    @mock.patch('website.project.tasks.settings.SHARE_API_TOKEN', 'totaly_real_token')
    @mock.patch('website.project.tasks.send_share_node_data')
    def test_approval_cancels_pending_embargoes_on_descendant_nodes(self, mock_update_share):
        # Initiate embargo for registration
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10),
            for_existing_registration=True
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        # Initiate retraction for parent registration
        self.registration.retract_registration(self.user)
        self.registration.save()
        assert_true(self.registration.is_pending_retraction)

        # Ensure descendant nodes are pending embargo
        descendants = self.registration.get_descendants_recursive()
        for node in descendants:
            assert_true(node.is_pending_retraction)
            assert_true(node.is_pending_embargo)

        # Approve parent registration's retraction
        approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        self.registration.retraction.approve_retraction(self.user, approval_token)
        assert_true(self.registration.is_retracted)
        self.registration.embargo.reload()
        assert_false(self.registration.is_pending_embargo)

        # Ensure descendant nodes are not pending embargo
        descendants = self.registration.get_descendants_recursive()
        for node in descendants:
            assert_true(node.is_retracted)
            assert_false(node.is_pending_embargo)

        assert mock_update_share.called

    @mock.patch('website.project.tasks.settings.SHARE_URL', 'ima_real_website')
    @mock.patch('website.project.tasks.settings.SHARE_API_TOKEN', 'totaly_real_token')
    @mock.patch('website.project.tasks.send_share_node_data')
    def test_approval_cancels_active_embargoes_on_descendant_nodes(self, mock_update_share):
        # Initiate embargo for registration
        self.registration.embargo_registration(
            self.user,
            timezone.now() + datetime.timedelta(days=10),
            for_existing_registration=True
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        # Approve embargo for registration
        embargo_approval_token = self.registration.embargo.approval_state[self.user._id]['approval_token']
        self.registration.embargo.approve_embargo(self.user, embargo_approval_token)
        assert_false(self.registration.is_pending_embargo)
        assert_true(self.registration.embargo_end_date)

        # Initiate retraction for parent registration
        self.registration.retract_registration(self.user)
        self.registration.save()
        assert_true(self.registration.is_pending_retraction)

        # Ensure descendant nodes are not pending embargo
        descendants = self.registration.get_descendants_recursive()
        for node in descendants:
            assert_true(node.is_pending_retraction)
            assert_true(node.embargo_end_date)

        # Approve parent registration's retraction
        approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        self.registration.retraction.approve_retraction(self.user, approval_token)
        assert_true(self.registration.is_retracted)

        # Ensure descendant nodes are not pending embargo
        descendants = self.registration.get_descendants_recursive()
        for node in descendants:
            assert_true(node.is_retracted)

        assert mock_update_share.called

@pytest.mark.enable_bookmark_creation
class RegistrationRetractionShareHook(OsfTestCase):
    def setUp(self):
        super(RegistrationRetractionShareHook, self).setUp()

        self.user = AuthUserFactory()
        self.auth = self.user.auth
        self.project = ProjectFactory(is_public=True, creator=self.user)

        self.registration = RegistrationFactory(project=self.project, is_public=True)
        # Reload the registration; else tests won't catch failures to svae
        self.registration.reload()

    @mock.patch('website.project.tasks.format_node')
    @mock.patch('website.project.tasks.format_registration')
    @mock.patch('website.project.tasks.settings.SHARE_URL', 'ima_real_website')
    @mock.patch('website.project.tasks.settings.SHARE_API_TOKEN', 'totaly_real_token')
    @mock.patch('website.project.tasks.send_share_node_data')
    def test_approval_calls_share_hook(self, mock_update_share, mock_format_registration, mock_format_node):
        # Initiate retraction for parent registration
        self.registration.retract_registration(self.user)
        self.registration.save()

        # Approve parent registration's retraction
        approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        self.registration.retraction.approve_retraction(self.user, approval_token)
        assert_true(self.registration.is_retracted)
        assert mock_update_share.called
        assert mock_format_registration.called
        assert not mock_format_node.called

    @mock.patch('website.project.tasks.settings.SHARE_URL', 'ima_real_website')
    @mock.patch('website.project.tasks.settings.SHARE_API_TOKEN', 'totaly_real_token')
    @mock.patch('website.project.tasks.send_share_node_data')
    def test_disapproval_does_not_call_share_hook(self, mock_update_share):
        # Initiate retraction for parent registration
        self.registration.retract_registration(self.user)
        self.registration.save()

        rejection_token = self.registration.retraction.approval_state[self.user._id]['rejection_token']
        self.registration.retraction.disapprove_retraction(self.user, rejection_token)
        assert_false(self.registration.is_retracted)
        assert not mock_update_share.called


@pytest.mark.enable_bookmark_creation
class RegistrationRetractionApprovalDisapprovalViewsTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationRetractionApprovalDisapprovalViewsTestCase, self).setUp()

        self.user = AuthUserFactory()
        self.registered_from = ProjectFactory(is_public=True, creator=self.user)
        self.registration = RegistrationFactory(is_public=True, project=self.registered_from)
        self.registration.retract_registration(self.user)
        self.registration.save()
        self.approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']
        self.rejection_token = self.registration.retraction.approval_state[self.user._id]['rejection_token']
        self.corrupt_token = fake.sentence()
        self.token_without_sanction = tokens.encode({
            'action': 'approve_retraction',
            'user_id': self.user._id,
            'sanction_id': 'invalid id'
        })

    # node_registration_retraction_approve_tests
    def test_GET_approve_from_unauthorized_user_returns_HTTPError_UNAUTHORIZED(self):
        unauthorized_user = AuthUserFactory()
        res = self.app.get(
            self.registration.web_url_for('token_action', token=self.approval_token),
            auth=unauthorized_user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http_status.HTTP_401_UNAUTHORIZED)

    def test_GET_approve_registration_without_retraction_returns_HTTPError_BAD_REQUEST(self):
        assert_true(self.registration.is_pending_retraction)
        self.registration.retraction.reject(self.user, self.rejection_token)
        assert_false(self.registration.is_pending_retraction)
        self.registration.retraction.save()

        res = self.app.get(
            self.registration.web_url_for('token_action', token=self.approval_token),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_GET_approve_with_invalid_token_returns_HTTPError_BAD_REQUEST(self):
        res = self.app.get(
            self.registration.web_url_for('token_action', token=self.corrupt_token),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_GET_approve_with_non_existant_sanction_returns_HTTPError_BAD_REQUEST(self):
        res = self.app.get(
            self.registration.web_url_for('token_action', token=self.token_without_sanction),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_GET_approve_with_valid_token_returns_302(self):
        res = self.app.get(
            self.registration.web_url_for('token_action', token=self.approval_token),
            auth=self.user.auth
        )
        self.registration.retraction.reload()
        assert_true(self.registration.is_retracted)
        assert_false(self.registration.is_pending_retraction)
        assert_equal(res.status_code,  http_status.HTTP_302_FOUND)

    # node_registration_retraction_disapprove_tests
    def test_GET_disapprove_from_unauthorized_user_returns_HTTPError_UNAUTHORIZED(self):
        unauthorized_user = AuthUserFactory()

        res = self.app.get(
            self.registration.web_url_for('token_action', token=self.rejection_token),
            auth=unauthorized_user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http_status.HTTP_401_UNAUTHORIZED)

    def test_GET_disapprove_registration_without_retraction_returns_HTTPError_BAD_REQUEST(self):
        assert_true(self.registration.is_pending_retraction)
        self.registration.retraction.reject(self.user, self.rejection_token)
        assert_false(self.registration.is_pending_retraction)
        self.registration.retraction.save()

        res = self.app.get(
            self.registration.web_url_for('token_action', token=self.rejection_token),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_GET_disapprove_with_invalid_token_HTTPError_BAD_REQUEST(self):
        res = self.app.get(
            self.registration.web_url_for('token_action', token=self.corrupt_token),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_GET_disapprove_with_valid_token_returns_redirect(self):
        res = self.app.get(
            self.registration.web_url_for('token_action', token=self.rejection_token),
            auth=self.user.auth,
        )
        self.registration.retraction.reload()
        assert_false(self.registration.is_retracted)
        assert_false(self.registration.is_pending_retraction)
        assert_true(self.registration.retraction.is_rejected)
        assert_equal(res.status_code, http_status.HTTP_302_FOUND)


@pytest.mark.enable_bookmark_creation
class ComponentRegistrationRetractionViewsTestCase(OsfTestCase):
    def setUp(self):
        super(ComponentRegistrationRetractionViewsTestCase, self).setUp()
        self.user = AuthUserFactory()
        self.auth = self.user.auth
        self.project = ProjectFactory(is_public=True, creator=self.user)
        self.component = NodeFactory(
            is_public=True,
            creator=self.user,
            parent=self.project,
            title='Component'
        )
        self.subproject = ProjectFactory(
            is_public=True,
            creator=self.user,
            parent=self.project,
            title='Subproject'
        )
        self.subproject_component = NodeFactory(
            is_public=True,
            creator=self.user,
            parent=self.subproject,
            title='Subcomponent'
        )
        self.registration = RegistrationFactory(is_public=True, project=self.project)
        self.component_registration = self.registration._nodes.order_by('created').first()
        self.subproject_registration = list(self.registration._nodes.order_by('created'))[1]
        self.subproject_component_registration = self.subproject_registration._nodes.order_by('created').first()

    def test_POST_retraction_to_component_returns_HTTPError_BAD_REQUEST(self):
        res = self.app.post_json(
            self.component_registration.api_url_for('node_registration_retraction_post'),
            auth=self.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_POST_retraction_to_subproject_returns_HTTPError_BAD_REQUEST(self):
        res = self.app.post_json(
            self.subproject_registration.api_url_for('node_registration_retraction_post'),
            auth=self.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_POST_retraction_to_subproject_component_returns_HTTPError_BAD_REQUEST(self):
        res = self.app.post_json(
            self.subproject_component_registration.api_url_for('node_registration_retraction_post'),
            auth=self.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, http_status.HTTP_400_BAD_REQUEST)

@pytest.mark.enable_bookmark_creation
class RegistrationRetractionViewsTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationRetractionViewsTestCase, self).setUp()

        self.user = AuthUserFactory()
        self.registered_from = ProjectFactory(creator=self.user, is_public=True)
        self.registration = RegistrationFactory(project=self.registered_from, is_public=True)

        self.retraction_post_url = self.registration.api_url_for('node_registration_retraction_post')
        self.retraction_get_url = self.registration.web_url_for('node_registration_retraction_get')
        self.justification = fake.sentence()

        self.group_mem = AuthUserFactory()
        self.group = OSFGroupFactory(creator=self.group_mem)
        self.registration.registered_from.add_osf_group(self.group, permissions.ADMIN)

    def test_GET_retraction_page_when_pending_retraction_returns_HTTPError_BAD_REQUEST(self):
        self.registration.retract_registration(self.user)
        self.registration.save()

        res = self.app.get(
            self.retraction_get_url,
            auth=self.user.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_POST_retraction_to_private_registration_returns_HTTPError_FORBIDDEN(self):
        self.registration.is_public = False
        self.registration.save()

        res = self.app.post_json(
            self.retraction_post_url,
            {'justification': ''},
            auth=self.user.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, http_status.HTTP_403_FORBIDDEN)
        self.registration.reload()
        assert_is_none(self.registration.retraction)

    @mock.patch('website.mails.send_mail')
    def test_POST_retraction_does_not_send_email_to_unregistered_admins(self, mock_send_mail):
        unreg = UnregUserFactory()
        self.registration.add_unregistered_contributor(
            unreg.fullname,
            unreg.email,
            auth=Auth(self.user),
            permissions=permissions.ADMIN,
            existing_user=unreg
        )
        self.registration.save()
        self.app.post_json(
            self.retraction_post_url,
            {'justification': ''},
            auth=self.user.auth,
        )
        # Only the creator gets an email; the unreg user does not get emailed
        assert_equal(mock_send_mail.call_count, 1)

    def test_POST_pending_embargo_returns_HTTPError_HTTPOK(self):
        self.registration.embargo_registration(
            self.user,
            (timezone.now() + datetime.timedelta(days=10)),
            for_existing_registration=True
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        res = self.app.post_json(
            self.retraction_post_url,
            {'justification': ''},
            auth=self.user.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, http_status.HTTP_200_OK)
        self.registration.reload()
        assert_true(self.registration.is_pending_retraction)

    def test_POST_active_embargo_returns_HTTPOK(self):
        self.registration.embargo_registration(
            self.user,
            (timezone.now() + datetime.timedelta(days=10)),
            for_existing_registration=True
        )
        self.registration.save()
        assert_true(self.registration.is_pending_embargo)

        approval_token = self.registration.embargo.approval_state[self.user._id]['approval_token']
        self.registration.embargo.approve(self.user, approval_token)
        assert_true(self.registration.embargo_end_date)

        res = self.app.post_json(
            self.retraction_post_url,
            {'justification': ''},
            auth=self.user.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, http_status.HTTP_200_OK)
        self.registration.reload()
        assert_true(self.registration.is_pending_retraction)

    def test_POST_retraction_by_non_admin_retract_HTTPError_UNAUTHORIZED(self):
        res = self.app.post_json(self.retraction_post_url, expect_errors=True)
        assert_equals(res.status_code, http_status.HTTP_401_UNAUTHORIZED)
        self.registration.reload()
        assert_is_none(self.registration.retraction)

        # group admin POST fails
        res = self.app.post_json(self.retraction_post_url, auth=self.group_mem.auth, expect_errors=True)
        assert_equal(res.status_code, http_status.HTTP_403_FORBIDDEN)

    @mock.patch('website.mails.send_mail')
    def test_POST_retraction_without_justification_returns_HTTPOK(self, mock_send):
        res = self.app.post_json(
            self.retraction_post_url,
            {'justification': ''},
            auth=self.user.auth,
        )
        assert_equal(res.status_code, http_status.HTTP_200_OK)
        self.registration.reload()
        assert_false(self.registration.is_retracted)
        assert_true(self.registration.is_pending_retraction)
        assert_is_none(self.registration.retraction.justification)

    @mock.patch('website.mails.send_mail')
    def test_valid_POST_retraction_adds_to_parent_projects_log(self, mock_send):
        initial_project_logs = self.registration.registered_from.logs.count()
        self.app.post_json(
            self.retraction_post_url,
            {'justification': ''},
            auth=self.user.auth,
        )
        self.registration.registered_from.reload()
        # Logs: Created, registered, retraction initiated
        assert_equal(self.registration.registered_from.logs.count(), initial_project_logs + 1)

    @mock.patch('website.mails.send_mail')
    def test_valid_POST_retraction_when_pending_retraction_raises_400(self, mock_send):
        self.app.post_json(
            self.retraction_post_url,
            {'justification': ''},
            auth=self.user.auth,
        )
        res = self.app.post_json(
            self.retraction_post_url,
            {'justification': ''},
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    @mock.patch('website.mails.send_mail')
    def test_valid_POST_calls_send_mail_with_username(self, mock_send):
        self.app.post_json(
            self.retraction_post_url,
            {'justification': ''},
            auth=self.user.auth,
        )
        assert_true(mock_send.called)
        args, kwargs = mock_send.call_args
        assert_true(self.user.username in args)

    def test_non_contributor_GET_approval_returns_HTTPError_UNAUTHORIZED(self):
        non_contributor = AuthUserFactory()
        self.registration.retract_registration(self.user)
        approval_token = self.registration.retraction.approval_state[self.user._id]['approval_token']

        approval_url = self.registration.web_url_for('token_action', token=approval_token)
        res = self.app.get(approval_url, auth=non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, http_status.HTTP_401_UNAUTHORIZED)
        assert_true(self.registration.is_pending_retraction)
        assert_false(self.registration.is_retracted)

        # group admin on node fails disapproval GET
        res = self.app.get(approval_url, auth=self.group_mem.auth, expect_errors=True)
        assert_equal(res.status_code, http_status.HTTP_401_UNAUTHORIZED)

    def test_non_contributor_GET_disapproval_returns_HTTPError_UNAUTHORIZED(self):
        non_contributor = AuthUserFactory()
        self.registration.retract_registration(self.user)
        rejection_token = self.registration.retraction.approval_state[self.user._id]['rejection_token']

        disapproval_url = self.registration.web_url_for('token_action', token=rejection_token)
        res = self.app.get(disapproval_url, auth=non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, http_status.HTTP_401_UNAUTHORIZED)
        assert_true(self.registration.is_pending_retraction)
        assert_false(self.registration.is_retracted)

        # group admin on node fails disapproval GET
        res = self.app.get(disapproval_url, auth=self.group_mem.auth, expect_errors=True)
        assert_equal(res.status_code, http_status.HTTP_401_UNAUTHORIZED)
