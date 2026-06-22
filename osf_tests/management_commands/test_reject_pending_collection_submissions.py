import pytest
from unittest import mock
from django.db import IntegrityError
from transitions import MachineError

from osf.management.commands.reject_pending_collection_submissions import (
    DEFAULT_COMMENT,
    reject_pending_collection_submissions,
)
from osf.models import CollectionSubmission
from osf.utils.workflows import CollectionSubmissionStates
from osf_tests.factories import (
    AuthUserFactory,
    CollectionFactory,
    CollectionProviderFactory,
    NodeFactory,
)
from tests.utils import capture_notifications


@pytest.fixture()
def actor():
    return AuthUserFactory()


@pytest.fixture()
def moderated_provider():
    provider = CollectionProviderFactory()
    provider.reviews_workflow = 'pre-moderation'
    provider.update_group_permissions()
    provider.save()
    return provider


@pytest.fixture()
def moderated_collection(moderated_provider):
    collection = CollectionFactory()
    collection.provider = moderated_provider
    collection.save()
    return collection


def make_pending_submission(collection):
    node = NodeFactory(is_public=True)
    submission = CollectionSubmission(
        guid=node.guids.first(),
        collection=collection,
        creator=node.creator,
    )
    with capture_notifications():
        submission.save()
    assert submission.state == CollectionSubmissionStates.PENDING
    return submission


@pytest.mark.django_db
class TestRejectPendingCollectionSubmissions:

    def test_rejects_pending_submission(self, actor, moderated_collection):
        submission = make_pending_submission(moderated_collection)

        with capture_notifications():
            count = reject_pending_collection_submissions(user_guid=actor._id, comment=None)

        assert count == 1
        submission.refresh_from_db()
        assert submission.state == CollectionSubmissionStates.REJECTED
        action = submission.actions.order_by('-created').first()
        assert action.comment == DEFAULT_COMMENT

    def test_skips_non_pending_submissions(self, actor, moderated_collection):
        pending = make_pending_submission(moderated_collection)
        accepted = make_pending_submission(moderated_collection)
        accepted.machine_state = CollectionSubmissionStates.ACCEPTED.value
        accepted.save()

        with capture_notifications():
            count = reject_pending_collection_submissions(user_guid=actor._id, comment=None)

        assert count == 1
        pending.refresh_from_db()
        accepted.refresh_from_db()
        assert pending.state == CollectionSubmissionStates.REJECTED
        assert accepted.state == CollectionSubmissionStates.ACCEPTED

    def test_dry_run_does_not_change_state(self, actor, moderated_collection):
        submission = make_pending_submission(moderated_collection)
        with capture_notifications():
            count = reject_pending_collection_submissions(user_guid=actor._id, comment=None, dry_run=True)
        assert count == 1
        submission.refresh_from_db()
        assert submission.state == CollectionSubmissionStates.PENDING

    def test_invalid_user_guid_raises(self):
        with pytest.raises(RuntimeError, match='Could not find user'):
            reject_pending_collection_submissions(user_guid='notavalidguid', comment=None)

    def test_custom_comment(self, actor, moderated_collection):
        submission = make_pending_submission(moderated_collection)
        custom_comment = 'Rejected due to policy update.'

        with capture_notifications():
            reject_pending_collection_submissions(user_guid=actor._id, comment=custom_comment)

        action = submission.actions.order_by('-created').first()
        assert action.comment == custom_comment

    def test_machine_error_is_handled_gracefully(self, actor, moderated_collection):
        submission_1 = make_pending_submission(moderated_collection)
        submission_2 = make_pending_submission(moderated_collection)

        def patched_validate_reject(self, event_data):
            if self.pk == submission_1.pk:
                raise MachineError('Simulated error')

        with mock.patch.object(CollectionSubmission, '_validate_reject', patched_validate_reject):
            with capture_notifications():
                count = reject_pending_collection_submissions(user_guid=actor._id, comment=None)

        assert count == 1
        submission_1.refresh_from_db()
        submission_2.refresh_from_db()
        assert submission_1.state == CollectionSubmissionStates.PENDING
        assert submission_2.state == CollectionSubmissionStates.REJECTED

    def test_db_failure_on_one_submission_does_not_block_others(self, actor, moderated_collection):
        submission_1 = make_pending_submission(moderated_collection)
        submission_2 = make_pending_submission(moderated_collection)
        original_save_transition = CollectionSubmission._save_transition

        def patched_save_transition(self, event_data):
            if self.pk == submission_1.pk:
                self.save()
                raise IntegrityError('Simulated DB failure')
            return original_save_transition(self, event_data)

        with mock.patch.object(CollectionSubmission, '_save_transition', patched_save_transition):
            with capture_notifications():
                count = reject_pending_collection_submissions(user_guid=actor._id, comment=None)

        assert count == 1
        submission_1.refresh_from_db()
        submission_2.refresh_from_db()
        assert submission_1.state == CollectionSubmissionStates.PENDING
        assert submission_2.state == CollectionSubmissionStates.REJECTED
