import pytest
from unittest import mock
from django.db import IntegrityError
from transitions import MachineError

from osf.management.commands.reject_pending_node_requests import (
    DEFAULT_COMMENT,
    reject_pending_node_requests,
)
from osf.models import NodeRequest
from osf.utils.workflows import NodeRequestTypes
from osf_tests.factories import (
    AuthUserFactory,
    NodeFactory,
    NodeRequestFactory,
    RegistrationFactory,
)
from tests.utils import capture_notifications


@pytest.fixture()
def actor():
    return AuthUserFactory()


def make_pending_request(request_type=NodeRequestTypes.ACCESS.value, target=None, creator=None):
    return NodeRequestFactory(
        target=target or NodeFactory(),
        creator=creator or AuthUserFactory(),
        request_type=request_type,
        machine_state='pending',
    )


@pytest.mark.django_db
class TestRejectPendingNodeRequests:

    def test_rejects_pending_access_request(self, actor):
        node_request = make_pending_request()

        with capture_notifications():
            count = reject_pending_node_requests(user_guid=actor._id, comment=None)

        assert count == 1
        node_request.refresh_from_db()
        assert node_request.machine_state == 'rejected'
        action = node_request.actions.order_by('-created').first()
        assert action.comment == DEFAULT_COMMENT

    def test_rejects_pending_institutional_request(self, actor):
        node_request = make_pending_request(request_type=NodeRequestTypes.INSTITUTIONAL_REQUEST.value)

        with capture_notifications():
            count = reject_pending_node_requests(user_guid=actor._id, comment=None)

        assert count == 1
        node_request.refresh_from_db()
        assert node_request.machine_state == 'rejected'

    def test_skips_withdrawal_requests(self, actor):
        registration = RegistrationFactory()
        withdrawal_request = NodeRequestFactory(
            target=registration,
            request_type=NodeRequestTypes.WITHDRAWAL.value,
            machine_state='pending',
        )
        access_request = make_pending_request()

        with capture_notifications():
            count = reject_pending_node_requests(user_guid=actor._id, comment=None)

        assert count == 1
        withdrawal_request.refresh_from_db()
        access_request.refresh_from_db()
        assert withdrawal_request.machine_state == 'pending'
        assert access_request.machine_state == 'rejected'

    def test_skips_non_pending_requests(self, actor):
        pending = make_pending_request()
        accepted = make_pending_request()
        accepted.machine_state = 'accepted'
        accepted.save()

        with capture_notifications():
            count = reject_pending_node_requests(user_guid=actor._id, comment=None)

        assert count == 1
        pending.refresh_from_db()
        accepted.refresh_from_db()
        assert pending.machine_state == 'rejected'
        assert accepted.machine_state == 'accepted'

    def test_dry_run_does_not_change_state(self, actor):
        node_request = make_pending_request()

        with capture_notifications():
            count = reject_pending_node_requests(user_guid=actor._id, comment=None, dry_run=True)

        assert count == 1
        node_request.refresh_from_db()
        assert node_request.machine_state == 'pending'

    def test_invalid_user_guid_raises(self):
        with pytest.raises(RuntimeError, match='Could not find user'):
            reject_pending_node_requests(user_guid='notavalidguid', comment=None)

    def test_custom_comment(self, actor):
        node_request = make_pending_request()
        custom_comment = 'Rejected due to policy update.'

        with capture_notifications():
            reject_pending_node_requests(user_guid=actor._id, comment=custom_comment)

        action = node_request.actions.order_by('-created').first()
        assert action.comment == custom_comment

    def test_disabled_requester_does_not_block_command(self, actor):
        requester = AuthUserFactory()
        requester.is_disabled = True
        requester.save()
        node_request = make_pending_request(creator=requester)

        with capture_notifications():
            count = reject_pending_node_requests(user_guid=actor._id, comment=None)

        assert count == 1
        node_request.refresh_from_db()
        assert node_request.machine_state == 'rejected'

    def test_machine_error_is_handled_gracefully(self, actor):
        request_1 = make_pending_request()
        request_2 = make_pending_request()

        def patched_run_reject(self, user, comment):
            if self.pk == request_1.pk:
                raise MachineError('Simulated error')
            return NodeRequest.run_reject(self, user=user, comment=comment)

        with mock.patch.object(NodeRequest, 'run_reject', patched_run_reject):
            with capture_notifications():
                count = reject_pending_node_requests(user_guid=actor._id, comment=None)

        assert count == 1
        request_1.refresh_from_db()
        request_2.refresh_from_db()
        assert request_1.machine_state == 'pending'
        assert request_2.machine_state == 'rejected'

    def test_db_failure_on_one_request_does_not_block_others(self, actor):
        request_1 = make_pending_request()
        request_2 = make_pending_request()
        original_run_reject = NodeRequest.run_reject

        def patched_run_reject(self, user, comment):
            if self.pk == request_1.pk:
                raise IntegrityError('Simulated DB failure')
            return original_run_reject(self, user=user, comment=comment)

        with mock.patch.object(NodeRequest, 'run_reject', patched_run_reject):
            with capture_notifications():
                count = reject_pending_node_requests(user_guid=actor._id, comment=None)

        assert count == 1
        request_1.refresh_from_db()
        request_2.refresh_from_db()
        assert request_1.machine_state == 'pending'
        assert request_2.machine_state == 'rejected'
