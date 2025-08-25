import pytest
from waffle.testutils import override_switch
from osf import features
from osf.models import NotificationType
from osf.utils.workflows import DefaultStates
from osf_tests.factories import PreprintFactory, AuthUserFactory
from tests.utils import get_mailhog_messages, delete_mailhog_messages, capture_notifications, assert_emails


@pytest.mark.django_db
class TestReviewable:

    @override_switch(features.ENABLE_MAILHOG, active=True)
    def test_reject_resubmission_sends_emails(self):
        user = AuthUserFactory()
        preprint = PreprintFactory(
            reviews_workflow='pre-moderation',
            is_published=False
        )
        assert preprint.machine_state == DefaultStates.INITIAL.value
        delete_mailhog_messages()
        with capture_notifications(passthrough=True) as notifications:
            preprint.run_submit(user)
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.PROVIDER_REVIEWS_SUBMISSION_CONFIRMATION
        assert preprint.machine_state == DefaultStates.PENDING.value

        assert not user.notification_subscriptions.exists()
        preprint.run_reject(user, 'comment')
        assert preprint.machine_state == DefaultStates.REJECTED.value

        massages = get_mailhog_messages()
        assert massages['count'] == len(notifications['emails'])
        assert_emails(massages, notifications)

        delete_mailhog_messages()
        with capture_notifications(passthrough=True) as notifications:
            preprint.run_submit(user)  # Resubmission alerts users and moderators
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.PROVIDER_REVIEWS_RESUBMISSION_CONFIRMATION
        assert preprint.machine_state == DefaultStates.PENDING.value
        massages = get_mailhog_messages()
        assert massages['count'] == len(notifications['emails'])
        assert_emails(massages, notifications)

        delete_mailhog_messages()
