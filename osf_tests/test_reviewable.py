from unittest import mock
import pytest

from osf.models import Preprint
from osf.utils.workflows import DefaultStates
from osf_tests.factories import PreprintFactory, AuthUserFactory
from website import mails


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

    @mock.patch('website.reviews.listeners.mails.send_mail')
    def test_reject_resubmission_sends_emails(self, send_mail):
        user = AuthUserFactory()
        preprint = PreprintFactory(
            reviews_workflow='pre-moderation',
            is_published=False
        )
        assert preprint.machine_state == DefaultStates.INITIAL.value
        assert not send_mail.call_count

        preprint.run_submit(user)
        assert send_mail.call_count == 1
        assert preprint.machine_state == DefaultStates.PENDING.value
        mail_template = send_mail.call_args[0][1]
        assert mail_template == mails.REVIEWS_SUBMISSION_CONFIRMATION

        assert not user.notification_subscriptions.exists()
        preprint.run_reject(user, 'comment')
        assert preprint.machine_state == DefaultStates.REJECTED.value

        preprint.run_submit(user)  # Resubmission alerts users and moderators
        assert preprint.machine_state == DefaultStates.PENDING.value
        mail_template = send_mail.call_args[0][1]
        assert send_mail.call_count == 2
        assert mail_template == mails.REVIEWS_RESUBMISSION_CONFIRMATION
