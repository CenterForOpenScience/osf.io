# -*- coding: utf-8 -*-
"""Tests ported from tests/test_sanctions.py and tests/test_registrations.py"""
import mock
import pytest
import datetime

from django.utils import timezone
from django.contrib.auth.models import Permission

from nose.tools import assert_raises
from transitions import MachineError

from osf.models import DraftRegistrationApproval, NodeLog, RegistrationSchema
from osf.exceptions import NodeStateError
from osf_tests import factories
from osf_tests.utils import mock_archive
from osf.utils import permissions


@pytest.mark.django_db
class TestRegistrationApprovalHooks:

    # Regression test for https://openscience.atlassian.net/browse/OSF-4940
    @mock.patch('osf.models.node.AbstractNode.update_search')
    def test_unmoderated_accept_sets_state_to_approved(self, mock_update_search):
        user = factories.UserFactory()
        registration = factories.RegistrationFactory(creator=user)
        registration.require_approval(user)

        assert registration.registration_approval.is_pending_approval is True  # sanity check
        registration.registration_approval.accept()
        assert registration.registration_approval.is_pending_approval is False


@pytest.mark.django_db
class TestNodeEmbargoTerminations:

    @pytest.fixture()
    def user(self):
        return factories.UserFactory()

    @pytest.fixture()
    def node(self, user):
        return factories.ProjectFactory(creator=user)

    @pytest.yield_fixture()
    def registration(self, node):
        with mock_archive(node, embargo=True, autoapprove=True) as registration:
            yield registration

    @pytest.fixture()
    def not_embargoed(self):
        return factories.RegistrationFactory()

    def test_request_embargo_termination_not_embargoed(self, user, not_embargoed):
        with pytest.raises(NodeStateError):
            not_embargoed.request_embargo_termination(user)

    def test_terminate_embargo_makes_registrations_public(self, registration, user):
        registration.terminate_embargo()
        for node in registration.node_and_primary_descendants():
            assert node.is_public is True
            assert node.is_embargoed is False

    def test_terminate_embargo_adds_log_to_registered_from(self, node, registration, user):
        registration.terminate_embargo()
        last_log = node.logs.first()
        assert last_log.action == NodeLog.EMBARGO_COMPLETED

    def test_terminate_embargo_log_is_nouser(self, node, user, registration):
        registration.terminate_embargo(forced=True)
        last_log = node.logs.first()
        assert last_log.action == NodeLog.EMBARGO_TERMINATED
        assert last_log.user is None


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestDraftRegistrationApprovals:

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_on_complete_immediate_creates_registration_for_draft_initiator(self, mock_enquque):
        user = factories.UserFactory()
        project = factories.ProjectFactory(creator=user)
        registration_schema = RegistrationSchema.objects.get(name='Prereg Challenge', schema_version=2)
        draft = factories.DraftRegistrationFactory(
            branched_from=project,
            registration_schema=registration_schema,
        )
        approval = DraftRegistrationApproval(
            meta={
                'registration_choice': 'immediate'
            }
        )
        approval.save()
        draft.approval = approval
        draft.save()
        approval._on_complete(user)
        draft.reload()
        registered_node = draft.registered_node

        assert registered_node is not None
        assert registered_node.is_pending_registration
        assert registered_node.registered_user == draft.initiator

    # Regression test for https://openscience.atlassian.net/browse/OSF-8280
    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_approval_after_initiator_is_merged_into_another_user(self, mock_enqueue):
        approver = factories.UserFactory()
        administer_permission = Permission.objects.get(codename='administer_prereg')
        approver.user_permissions.add(administer_permission)
        approver.save()

        mergee = factories.UserFactory(fullname='Manny Mergee')
        merger = factories.UserFactory(fullname='Merve Merger')
        project = factories.ProjectFactory(creator=mergee)
        registration_schema = RegistrationSchema.objects.get(name='Prereg Challenge', schema_version=2)
        draft = factories.DraftRegistrationFactory(
            branched_from=project,
            registration_schema=registration_schema,
        )
        merger.merge_user(mergee)
        approval = DraftRegistrationApproval(
            meta={
                'registration_choice': 'immediate'
            }
        )
        approval.save()
        draft.approval = approval
        draft.save()
        approval.approve(approver)

        draft.reload()
        registered_node = draft.registered_node
        assert registered_node.registered_user == merger

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_on_complete_embargo_creates_registration_for_draft_initiator(self, mock_enquque):
        user = factories.UserFactory()
        end_date = timezone.now() + datetime.timedelta(days=366)  # <- leap year
        approval = DraftRegistrationApproval(
            meta={
                'registration_choice': 'embargo',
                'embargo_end_date': end_date.isoformat()
            }
        )
        approval.save()
        project = factories.ProjectFactory(creator=user)
        registration_schema = RegistrationSchema.objects.get(name='Prereg Challenge', schema_version=2)
        draft = factories.DraftRegistrationFactory(
            branched_from=project,
            registration_schema=registration_schema,
        )
        draft.approval = approval
        draft.save()

        approval._on_complete(user)
        draft.reload()
        registered_node = draft.registered_node
        assert registered_node is not None
        assert registered_node.is_pending_embargo
        assert registered_node.registered_user == draft.initiator

    def test_approval_requires_only_a_single_authorizer(self):
        approval = DraftRegistrationApproval(
            meta={
                'registration_choice': 'immediate',
            }
        )
        approval.save()
        with mock.patch.object(approval, '_on_complete') as mock_on_complete:
            authorizer1 = factories.AuthUserFactory()
            administer_permission = Permission.objects.get(codename='administer_prereg')
            authorizer1.user_permissions.add(administer_permission)
            authorizer1.save()
            approval.approve(authorizer1)
            assert mock_on_complete.called
            assert approval.is_approved

    @mock.patch('osf.models.DraftRegistrationApproval._send_rejection_email')
    def test_on_reject(self, mock_send_mail):
        user = factories.UserFactory()
        approval = DraftRegistrationApproval(
            meta={
                'registration_choice': 'immediate'
            }
        )
        approval.save()
        project = factories.ProjectFactory(creator=user)
        registration_schema = RegistrationSchema.objects.get(name='Prereg Challenge', schema_version=2)
        draft = factories.DraftRegistrationFactory(
            branched_from=project,
            registration_schema=registration_schema,
        )
        draft.approval = approval
        draft.save()
        approval._on_reject(user)
        assert approval.meta == {}
        assert mock_send_mail.call_count == 1

@pytest.mark.django_db
class TestRegistrationEmbargoTermination:

    @pytest.fixture()
    def user(self):
        return factories.AuthUserFactory()

    @pytest.fixture()
    def user2(self):
        return factories.AuthUserFactory()

    @pytest.fixture()
    def registration_with_contribs(self, user, user2):
        proj = factories.NodeFactory(creator=user)
        proj.add_contributor(user2, permissions.ADMIN)
        embargo = factories.EmbargoFactory()
        embargo.end_date = timezone.now() + datetime.timedelta(days=4)
        return factories.RegistrationFactory(project=proj, creator=user, embargo=embargo)

    @pytest.fixture()
    def embargo_termination(self, registration_with_contribs, user):
        return factories.EmbargoTerminationApprovalFactory(registration=registration_with_contribs, creator=user)

    def test_reject_then_approve_stays_rejected(self, user, user2, embargo_termination):
        user_1_tok = embargo_termination.token_for_user(user, 'rejection')
        user_2_tok = embargo_termination.token_for_user(user2, 'approval')
        embargo_termination.reject(user=user, token=user_1_tok)
        with assert_raises(MachineError):
            embargo_termination.approve(user=user2, token=user_2_tok)

        assert embargo_termination.is_rejected

    def test_single_approve_stays_unapproved(self, user, user2, embargo_termination):
        user_1_tok = embargo_termination.token_for_user(user, 'approval')
        embargo_termination.approve(user=user, token=user_1_tok)
        assert embargo_termination.state == embargo_termination.UNAPPROVED


@pytest.mark.django_db
class TestSanctionEmailRendering:

    @pytest.fixture
    def contributor(self):
        return factories.AuthUserFactory()

    @pytest.fixture(
        params=[
            factories.EmbargoFactory,
            factories.RegistrationApprovalFactory,
            factories.RetractionFactory,
            factories.EmbargoTerminationApprovalFactory,
        ]
    )
    def registration(self, request, contributor):
        sanction_factory = request.param
        sanction = sanction_factory(end_date=timezone.now())
        registration = sanction.target_registration
        registration.add_contributor(contributor)
        registration.save()
        return registration

    @mock.patch('website.mails.settings.USE_EMAIL', False)
    @pytest.mark.parametrize('reviews_workflow', [None, 'pre-moderation'])
    def test_render_admin_emails(self, registration, reviews_workflow):
        provider = registration.provider
        provider.reviews_workflow = reviews_workflow
        provider.save()

        registration.sanction.ask([(registration.creator, registration)])
        assert True  # mail rendered successfully

    @mock.patch('website.mails.settings.USE_EMAIL', False)
    @pytest.mark.parametrize('reviews_workflow', [None, 'pre-moderation'])
    def test_render_non_admin_emails(self, registration, reviews_workflow, contributor):
        provider = registration.provider
        provider.reviews_workflow = reviews_workflow
        provider.save()

        registration.sanction.ask([(contributor, registration)])
        assert True  # mail rendered successfully
