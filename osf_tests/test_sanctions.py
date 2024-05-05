"""Tests ported from tests/test_sanctions.py and tests/test_registrations.py"""
from unittest import mock
import pytest
import datetime

from django.utils import timezone
from transitions import MachineError

from osf.models import NodeLog
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

    @pytest.fixture()
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
        registration.refresh_from_db()
        for node in registration.node_and_primary_descendants():
            assert node.is_public is True
            assert node.is_embargoed is False
            assert node.moderation_state == 'accepted'

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
        with pytest.raises(MachineError):
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
    @pytest.mark.parametrize('branched_from_node', [True, False])
    def test_render_admin_emails(self, registration, reviews_workflow, branched_from_node):
        provider = registration.provider
        provider.reviews_workflow = reviews_workflow
        provider.save()

        registration.branched_from_node = branched_from_node
        registration.save()

        registration.sanction.ask([(registration.creator, registration)])
        assert True  # mail rendered successfully

    @mock.patch('website.mails.settings.USE_EMAIL', False)
    @pytest.mark.parametrize('reviews_workflow', [None, 'pre-moderation'])
    @pytest.mark.parametrize('branched_from_node', [True, False])
    def test_render_non_admin_emails(
            self, registration, reviews_workflow, branched_from_node, contributor):
        provider = registration.provider
        provider.reviews_workflow = reviews_workflow
        provider.save()

        registration.branched_from_node = branched_from_node
        registration.save()

        registration.sanction.ask([(contributor, registration)])
        assert True  # mail rendered successfully


@pytest.mark.django_db
class TestDOICreation:

    def make_test_registration(self, embargoed=False, moderated=False):
        sanction = factories.EmbargoFactory() if embargoed else factories.RegistrationApprovalFactory()
        registration = sanction.target_registration
        if moderated:
            provider = registration.provider
            provider.reviews_workflow = 'pre-moderation'
            provider.save()
        return registration

    def test_registration_approval__doi_minted_on_approval(self):
        registration = self.make_test_registration(embargoed=False, moderated=False)
        assert not registration.get_identifier(category='doi')

        registration.registration_approval.accept()
        assert registration.get_identifier_value(category='doi')

    def test_embargo__identifier_created_but_not_minted_on_aproval(self):
        registration = self.make_test_registration(embargoed=True, moderated=False)
        assert not registration.get_identifier(category='doi')

        registration.embargo.accept()
        assert registration.get_identifier(category='doi')
        assert not registration.get_identifier_value(category='doi')

    def test_embargo__identifier_minted_on_complete(self):
        registration = self.make_test_registration(embargoed=True, moderated=False)
        assert not registration.get_identifier(category='doi')

        registration.embargo.accept()
        identifier = registration.get_identifier(category='doi')

        registration.terminate_embargo()
        identifier.refresh_from_db()
        assert identifier.value

    @pytest.mark.parametrize('embargoed', [True, False])
    def test_moderated_sanction__no_identifier_created_until_moderator_approval(self, embargoed):
        registration = self.make_test_registration(embargoed=embargoed, moderated=True)
        provider = registration.provider
        provider.update_group_permissions()
        moderator = factories.AuthUserFactory()
        provider.get_group('moderator').user_set.add(moderator)

        # Admin approval
        registration.sanction.accept()
        assert not registration.get_identifier(category='doi')

        # Moderator approval

        with mock.patch('osf.models.node.AbstractNode.update_search'):
            registration.sanction.accept(user=moderator)
        assert registration.get_identifier(category='doi')
        # No value should be set if the registration was embargoed
        assert bool(registration.get_identifier_value(category='doi')) != embargoed

    @pytest.mark.parametrize('embargoed', [True, False])
    def test_nested_registration__identifier_created_on_approval(self, embargoed):
        registration = self.make_test_registration(embargoed=embargoed, moderated=False)

        child_project = factories.ProjectFactory(parent=registration.registered_from)
        grandchild_project = factories.ProjectFactory(parent=child_project)

        child_registration = factories.RegistrationFactory(parent=registration, project=child_project)
        grandchild_registration = factories.RegistrationFactory(parent=child_registration, project=grandchild_project)

        assert not child_registration.get_identifier(category='doi')
        assert not grandchild_registration.get_identifier(category='doi')

        registration.sanction.accept()
        assert child_registration.get_identifier(category='doi')
        assert grandchild_registration.get_identifier(category='doi')
        # No value should be set if the registrations were embargoed
        assert bool(child_registration.get_identifier_value(category='doi')) != embargoed
        assert bool(child_registration.get_identifier_value(category='doi')) != embargoed

    def test_nested_registration__embargoed_registration_gets_doi_on_termination(self):
        registration = self.make_test_registration(embargoed=True, moderated=False)

        child_project = factories.ProjectFactory(parent=registration.registered_from)
        grandchild_project = factories.ProjectFactory(parent=child_project)

        child_registration = factories.RegistrationFactory(parent=registration, project=child_project)
        grandchild_registration = factories.RegistrationFactory(parent=child_registration, project=grandchild_project)

        registration.embargo.accept()
        registration.terminate_embargo()

        assert child_registration.get_identifier_value('doi')
        assert grandchild_registration.get_identifier_value('doi')
