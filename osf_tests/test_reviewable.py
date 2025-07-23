from unittest import mock
import pytest

from osf.models import Preprint, NotificationType
from osf.utils.workflows import DefaultStates
from osf_tests.factories import PreprintFactory, AuthUserFactory
from tests.utils import capture_notifications


@pytest.mark.django_db
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

    def test_reject_resubmission_sends_emails(self):
        user = AuthUserFactory()
        preprint = PreprintFactory(
            reviews_workflow='pre-moderation',
            is_published=False
        )
        assert preprint.machine_state == DefaultStates.INITIAL.value

        with capture_notifications() as notifications:
            preprint.run_submit(user)
        assert len(notifications) == 1
        assert notifications[0]['type'] == NotificationType.Type.PROVIDER_REVIEWS_SUBMISSION_CONFIRMATION
        assert preprint.machine_state == DefaultStates.PENDING.value

        assert not user.notification_subscriptions.exists()
        preprint.run_reject(user, 'comment')
        assert preprint.machine_state == DefaultStates.REJECTED.value

        with capture_notifications() as notifications:
            preprint.run_submit(user)  # Resubmission alerts users and moderators
        assert len(notifications) == 1
        assert notifications[0]['type'] == NotificationType.Type.PROVIDER_REVIEWS_RESUBMISSION_CONFIRMATION
        assert preprint.machine_state == DefaultStates.PENDING.value
