from unittest import mock
import pytest

from osf.models import Preprint
from osf.utils.workflows import DefaultStates
from osf_tests.factories import PreprintFactory, AuthUserFactory


@pytest.mark.django_db
@pytest.mark.usefixtures('mock_send_grid')
@pytest.mark.usefixtures('mock_notification_send')
class TestReviewable:

    @mock.patch('website.identifiers.utils.request_identifiers')
    def test_state_changes(self, _):
        user = AuthUserFactory()
        preprint = PreprintFactory(reviews_workflow='pre-moderation', is_published=False)
        assert preprint.machine_state == DefaultStates.INITIAL.value

        preprint.run_submit(user)
        assert preprint.machine_state == DefaultStates.PENDING.value

        preprint.run_accept(user, 'comment')
        assert preprint.machine_state == DefaultStates.ACCEPTED.value
        from_db = Preprint.objects.get(id=preprint.id)
        assert from_db.machine_state == DefaultStates.ACCEPTED.value

        preprint.run_reject(user, 'comment')
        assert preprint.machine_state == DefaultStates.REJECTED.value
        from_db.refresh_from_db()
        assert from_db.machine_state == DefaultStates.REJECTED.value

        preprint.run_accept(user, 'comment')
        assert preprint.machine_state == DefaultStates.ACCEPTED.value
        from_db.refresh_from_db()
        assert from_db.machine_state == DefaultStates.ACCEPTED.value

    def test_reject_resubmission_sends_emails(self, mock_notification_send):
        user = AuthUserFactory()
        preprint = PreprintFactory(
            reviews_workflow='pre-moderation',
            is_published=False
        )
        assert preprint.machine_state == DefaultStates.INITIAL.value
        assert not mock_notification_send.call_count

        preprint.run_submit(user)
        assert mock_notification_send.call_count == 1
        assert preprint.machine_state == DefaultStates.PENDING.value

        assert not user.notification_subscriptions.exists()
        preprint.run_reject(user, 'comment')
        assert preprint.machine_state == DefaultStates.REJECTED.value

        preprint.run_submit(user)  # Resubmission alerts users and moderators
        assert preprint.machine_state == DefaultStates.PENDING.value
        assert mock_notification_send.call_count == 2
