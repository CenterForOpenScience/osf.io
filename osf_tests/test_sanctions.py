# -*- coding: utf-8 -*-
"""Tests ported from tests/test_sanctions.py and tests/test_registrations.py"""
import mock
import pytest
import datetime

from django.utils import timezone

from osf.modm_compat import Q
from osf.models import DraftRegistrationApproval, MetaSchema
from osf_tests import factories
from osf_tests.utils import mock_archive

from framework.auth import Auth

from website import settings
from website.exceptions import NodeStateError
from website.project.model import NodeLog
from website.project.model import ensure_schemas


@pytest.mark.django_db
class TestRegistrationApprovalHooks:

    # Regression test for https://openscience.atlassian.net/browse/OSF-4940
    @mock.patch('osf.models.node.AbstractNode.update_search')
    def test_on_complete_sets_state_to_approved(self, mock_update_search):
        user = factories.UserFactory()
        registration = factories.RegistrationFactory(creator=user)
        registration.require_approval(user)

        assert registration.registration_approval.is_pending_approval is True  # sanity check
        registration.registration_approval._on_complete(None)
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
            not_embargoed.request_embargo_termination(Auth(user))

    def test_terminate_embargo_makes_registrations_public(self, registration, user):
        registration.terminate_embargo(Auth(user))
        for node in registration.node_and_primary_descendants():
            assert node.is_public is True
            assert node.is_embargoed is False

    def test_terminate_embargo_adds_log_to_registered_from(self, node, registration, user):
        registration.terminate_embargo(Auth(user))
        last_log = node.logs.first()
        assert last_log.action == NodeLog.EMBARGO_TERMINATED

    def test_terminate_embargo_log_is_nouser(self, node, user, registration):
        registration.terminate_embargo(Auth(user))
        last_log = node.logs.first()
        assert last_log.action == NodeLog.EMBARGO_TERMINATED
        assert last_log.user is None


@pytest.mark.django_db
class TestDraftRegistrationApprovals:

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    def test_on_complete_immediate_creates_registration_for_draft_initiator(self, mock_enquque):
        ensure_schemas()
        user = factories.UserFactory()
        project = factories.ProjectFactory(creator=user)
        registration_schema = MetaSchema.find_one(
            Q('name', 'eq', 'Prereg Challenge') &
            Q('schema_version', 'eq', 2)
        )
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
        ensure_schemas()
        registration_schema = MetaSchema.find_one(
            Q('name', 'eq', 'Prereg Challenge') &
            Q('schema_version', 'eq', 2)
        )
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
            authorizer1.add_system_tag(settings.PREREG_ADMIN_TAG)
            approval.approve(authorizer1)
            assert mock_on_complete.called
            assert approval.is_approved

    @mock.patch('website.mails.send_mail')
    def test_on_reject(self, mock_send_mail):
        user = factories.UserFactory()
        approval = DraftRegistrationApproval(
            meta={
                'registration_choice': 'immediate'
            }
        )
        approval.save()
        project = factories.ProjectFactory(creator=user)
        ensure_schemas()
        registration_schema = MetaSchema.find_one(
            Q('name', 'eq', 'Prereg Challenge') &
            Q('schema_version', 'eq', 2)
        )
        draft = factories.DraftRegistrationFactory(
            branched_from=project,
            registration_schema=registration_schema,
        )
        draft.approval = approval
        draft.save()
        approval._on_reject(user)
        assert approval.meta == {}
        assert mock_send_mail.call_count == 1
