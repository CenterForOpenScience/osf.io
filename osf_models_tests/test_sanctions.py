# -*- coding: utf-8 -*-
"""Tests ported from tests/test_sanctions.py."""
import mock
import pytest

from osf_models_tests import factories
from osf_models_tests.utils import mock_archive

from framework.auth import Auth

from website.exceptions import NodeStateError
from website.project.model import NodeLog

@pytest.mark.django_db
class TestRegistrationApprovalHooks:

    # Regression test for https://openscience.atlassian.net/browse/OSF-4940
    @mock.patch('osf_models.models.node.AbstractNode.update_search')
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
