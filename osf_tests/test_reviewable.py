from unittest import mock
import pytest

from addons.osfstorage.models import OsfStorageFile
from api_tests.utils import create_test_preprint_file
from framework.auth import Auth
from osf.models import Preprint, NotificationTypeEnum
from osf.utils.workflows import DefaultStates
from osf_tests.factories import PreprintFactory, AuthUserFactory
from tests.utils import capture_notifications
from website.files.exceptions import FileNodeIsPrimaryFile


def delete_primary_file(preprint):
    # Load the file fresh, like WaterButler's delete hook does, so it sees the preprint's current state
    OsfStorageFile.objects.get(id=preprint.primary_file_id).delete()
    preprint.refresh_from_db()


@pytest.mark.django_db
class TestReviewable:

    @mock.patch('website.identifiers.utils.request_identifiers')
    def test_state_changes(self, _):
        user = AuthUserFactory()
        preprint = PreprintFactory(reviews_workflow='pre-moderation', is_published=False)
        assert preprint.machine_state == DefaultStates.INITIAL.value

        with capture_notifications():
            preprint.run_submit(user)
        assert preprint.machine_state == DefaultStates.PENDING.value

        with capture_notifications():
            preprint.run_accept(user, 'comment')
        assert preprint.machine_state == DefaultStates.ACCEPTED.value
        from_db = Preprint.objects.get(id=preprint.id)
        assert from_db.machine_state == DefaultStates.ACCEPTED.value

        with capture_notifications():
            preprint.run_reject(user, 'comment')
        assert preprint.machine_state == DefaultStates.REJECTED.value
        from_db.refresh_from_db()
        assert from_db.machine_state == DefaultStates.REJECTED.value

        with capture_notifications():
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
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationTypeEnum.PROVIDER_REVIEWS_SUBMISSION_CONFIRMATION
        assert preprint.machine_state == DefaultStates.PENDING.value

        assert not user.notification_subscriptions.exists()
        with capture_notifications():
            preprint.run_reject(user, 'comment')
        assert preprint.machine_state == DefaultStates.REJECTED.value

        with capture_notifications() as notifications:
            preprint.run_submit(user)  # Resubmission alerts users and moderators
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationTypeEnum.PROVIDER_REVIEWS_RESUBMISSION_CONFIRMATION
        assert preprint.machine_state == DefaultStates.PENDING.value

    def test_submit_requires_primary_file(self):
        user = AuthUserFactory()
        preprint = PreprintFactory(reviews_workflow='pre-moderation', is_published=False, creator=user)
        delete_primary_file(preprint)
        assert preprint.primary_file is None

        with pytest.raises(ValueError, match='A primary file is required'):
            preprint.run_submit(user)
        preprint.refresh_from_db()
        assert preprint.machine_state == DefaultStates.INITIAL.value
        assert not preprint.actions.exists()

    def test_rejected_preprint_can_replace_primary_file_and_resubmit(self):
        user = AuthUserFactory()
        preprint = PreprintFactory(reviews_workflow='pre-moderation', is_published=False, creator=user)
        with capture_notifications():
            preprint.run_submit(user)
        with pytest.raises(FileNodeIsPrimaryFile):
            delete_primary_file(preprint)

        with capture_notifications():
            preprint.run_reject(user, 'wrong file')
        delete_primary_file(preprint)
        assert preprint.machine_state == DefaultStates.REJECTED.value
        assert preprint.primary_file is None

        with pytest.raises(ValueError, match='A primary file is required'):
            preprint.run_submit(user)
        preprint.refresh_from_db()
        assert preprint.machine_state == DefaultStates.REJECTED.value

        new_file = create_test_preprint_file(preprint, user, filename='correct_file.pdf')
        preprint.set_primary_file(new_file, auth=Auth(user), save=True)
        with capture_notifications():
            preprint.run_submit(user)
        assert preprint.machine_state == DefaultStates.PENDING.value
        assert preprint.primary_file == new_file
