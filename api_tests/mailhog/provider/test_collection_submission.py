import pytest
from waffle.testutils import override_switch
from osf import features
from osf_tests.factories import (
    AuthUserFactory,
    NodeFactory,
    CollectionProviderFactory,
    CollectionFactory,
)
from osf.models import NotificationType, CollectionSubmission
from tests.utils import get_mailhog_messages, delete_mailhog_messages, capture_notifications
from osf.utils.workflows import CollectionSubmissionStates

@pytest.fixture()
def moderated_collection_provider():
    collection_provider = CollectionProviderFactory()
    collection_provider.reviews_workflow = 'pre-moderation'
    moderator = AuthUserFactory()
    collection_provider.get_group('moderator').user_set.add(moderator)
    collection_provider.update_group_permissions()
    collection_provider.save()
    return collection_provider

@pytest.fixture()
def node(moderated_collection_provider):
    node = NodeFactory(is_public=True)
    node.save()
    return node

@pytest.fixture()
def moderated_collection(moderated_collection_provider):
    collection = CollectionFactory()
    collection.provider = moderated_collection_provider
    collection.save()
    return collection


@pytest.mark.django_db
class TestModeratedCollectionSubmission:

    @override_switch(features.ENABLE_MAILHOG, active=True)
    def test_notify_contributors_pending(self, node, moderated_collection):
        delete_mailhog_messages()
        with capture_notifications(passthrough=True) as notifications:
            collection_submission = CollectionSubmission(
                guid=node.guids.first(),
                collection=moderated_collection,
                creator=node.creator,
            )
            collection_submission.save()
        assert len(notifications['emits']) == 2
        assert notifications['emits'][0]['type'] == NotificationType.Type.COLLECTION_SUBMISSION_SUBMITTED
        assert notifications['emits'][1]['type'] == NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS
        assert collection_submission.state == CollectionSubmissionStates.PENDING
        massages = get_mailhog_messages()
        assert massages['count'] == len(notifications['emails'])
        # TODO check email content

        delete_mailhog_messages()

    @override_switch(features.ENABLE_MAILHOG, active=True)
    def test_notify_moderators_pending(self, node, moderated_collection):
        delete_mailhog_messages()
        with capture_notifications(passthrough=True) as notifications:
            collection_submission = CollectionSubmission(
                guid=node.guids.first(),
                collection=moderated_collection,
                creator=node.creator,
            )
            collection_submission.save()
        assert len(notifications['emits']) == 2
        assert notifications['emits'][0]['type'] == NotificationType.Type.COLLECTION_SUBMISSION_SUBMITTED
        assert notifications['emits'][1]['type'] == NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS
        assert collection_submission.state == CollectionSubmissionStates.PENDING
        massages = get_mailhog_messages()
        assert massages['count'] == len(notifications['emails'])
        # TODO check email content

        delete_mailhog_messages()
