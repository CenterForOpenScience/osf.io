import pytest
from api_tests.utils import UserRoles
from osf.utils.workflows import ApprovalStates
from osf_tests.factories import AuthUserFactory
from django.utils import timezone
from osf_tests.factories import NodeFactory, CollectionFactory, CollectionProviderFactory

from osf.models import CollectionSubmission
from osf.utils.workflows import CollectionSubmissionsTriggers, CollectionSubmissionStates

POST_URL = '/v2/collection_submission_actions/'


@pytest.fixture()
def collection_provider():
    collection_provider = CollectionProviderFactory()
    collection_provider.reviews_workflow = 'pre-moderation'
    collection_provider.update_group_permissions()
    collection_provider.save()
    return collection_provider


@pytest.fixture()
def node(collection_provider):
    node = NodeFactory(is_public=True)
    node.provider = collection_provider
    node.save()
    return node


@pytest.fixture()
def collection(collection_provider):
    collection = CollectionFactory()
    collection.provider = collection_provider
    collection.save()
    return collection


@pytest.fixture()
def collection_submission(node, collection):
    collection_submission = CollectionSubmission(
        guid=node.guids.first(),
        collection=collection,
        creator=node.creator,
    )
    collection_submission.save()
    return collection_submission


@pytest.fixture()
def collection_submission_action(collection_submission):
    action = collection_submission.actions.create(
        from_state=ApprovalStates.IN_PROGRESS,
        to_state=ApprovalStates.UNAPPROVED,
        trigger=CollectionSubmissionsTriggers.SUBMIT,
        creator=collection_submission.creator,
        comment='test comment'
    )
    return action


def make_payload(collection_submission, trigger='submit'):
    return {
        'data': {
            'type': 'collection-submission-actions',
            'attributes': {
                'comment': 'some comment',
                'trigger': trigger
            },
            'relationships': {
                'target': {
                    'data': {
                        'id': collection_submission._id,
                        'type': 'collection-submission'
                    }
                }
            }
        }
    }


def configure_test_auth(node, user_role):
    if user_role is UserRoles.UNAUTHENTICATED:
        return None

    user = AuthUserFactory()
    if user_role is UserRoles.MODERATOR:
        collection_submission = CollectionSubmission.objects.get(guid=node.guids.first())
        provider = collection_submission.collection.provider
        provider.get_group('moderator').user_set.add(user)
        provider.save()

    elif user_role in UserRoles.contributor_roles():
        node.add_contributor(user, user_role.get_permissions_string())

    return user.auth


@pytest.mark.django_db
class TestCollectionSubmissionsActionsListPOSTPermissions:

    @pytest.mark.parametrize('user_role', UserRoles.excluding(*[UserRoles.ADMIN_USER, UserRoles.MODERATOR]))
    def test_status_code__non_admin_moderator(self, app, node, collection_submission, user_role):
        test_auth = configure_test_auth(node, user_role)
        resp = app.post_json_api(
            POST_URL,
            make_payload(
                collection_submission,
                trigger=CollectionSubmissionsTriggers.ACCEPT.db_name
            ),
            auth=test_auth,
            expect_errors=True
        )
        expected_code = 403 if user_role is not UserRoles.UNAUTHENTICATED else 401
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('moderator_trigger', [CollectionSubmissionsTriggers.ACCEPT, CollectionSubmissionsTriggers.REJECT])
    def test_status_code__collection_moderator_accept_reject_moderated(self, app, node, collection_submission, moderator_trigger):
        collection_submission.state_machine.set_state(CollectionSubmissionStates.PENDING)
        collection_submission.save()
        test_auth = configure_test_auth(node, UserRoles.MODERATOR)
        resp = app.post_json_api(POST_URL, make_payload(
            collection_submission=collection_submission,
            trigger=moderator_trigger.db_name
        ), auth=test_auth, expect_errors=True)
        assert resp.status_code == 201

    @pytest.mark.parametrize('moderator_trigger', [CollectionSubmissionsTriggers.ACCEPT, CollectionSubmissionsTriggers.REJECT])
    @pytest.mark.parametrize('user_role', UserRoles.excluding(UserRoles.MODERATOR))
    def test_status_code__non_moderator_accept_reject_moderated(self, app, node, collection_submission, moderator_trigger, user_role):
        collection_submission.state_machine.set_state(CollectionSubmissionStates.PENDING)
        collection_submission.save()
        test_auth = configure_test_auth(node, user_role)
        resp = app.post_json_api(POST_URL, make_payload(
            collection_submission=collection_submission,
            trigger=moderator_trigger.db_name
        ), auth=test_auth, expect_errors=True)
        expected_code = 403 if user_role is not UserRoles.UNAUTHENTICATED else 401
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('user_role', UserRoles.excluding(*[UserRoles.MODERATOR, UserRoles.ADMIN_USER]))
    def test_status_code__non_moderator_admin_remove(self, app, node, collection_submission, user_role):
        collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        collection_submission.save()
        test_auth = configure_test_auth(node, user_role)
        resp = app.post_json_api(POST_URL, make_payload(
            collection_submission=collection_submission,
            trigger=CollectionSubmissionsTriggers.REMOVE.db_name
        ), auth=test_auth, expect_errors=True)
        expected_code = 403 if user_role is not UserRoles.UNAUTHENTICATED else 401
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('user_role', [UserRoles.MODERATOR, UserRoles.ADMIN_USER])
    def test_status_code__remove(self, app, node, collection_submission, user_role):
        collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        collection_submission.save()
        test_auth = configure_test_auth(node, user_role)
        resp = app.post_json_api(POST_URL, make_payload(
            collection_submission=collection_submission,
            trigger=CollectionSubmissionsTriggers.REMOVE.db_name
        ), auth=test_auth, expect_errors=True)
        assert resp.status_code == 201


@pytest.mark.django_db
class TestSubmissionsActionsListPOSTBehavior:

    @pytest.mark.parametrize('state', CollectionSubmissionStates.excluding(CollectionSubmissionStates.IN_PROGRESS))
    def test_POST_submit__fails(self, state, app, node, collection_submission):
        collection_submission.state_machine.set_state(state)
        collection_submission.save()
        test_auth = configure_test_auth(node, UserRoles.MODERATOR)
        payload = make_payload(collection_submission, trigger=CollectionSubmissionsTriggers.SUBMIT.db_name)
        resp = app.post_json_api(POST_URL, payload, auth=test_auth, expect_errors=True)
        assert resp.status_code == 409

    def test_POST_accept__writes_action_and_advances_state(self, app, collection_submission, node):
        collection_submission.state_machine.set_state(CollectionSubmissionStates.PENDING)
        collection_submission.save()
        test_auth = configure_test_auth(node, UserRoles.MODERATOR)
        payload = make_payload(collection_submission, trigger=CollectionSubmissionsTriggers.ACCEPT.db_name)
        app.post_json_api(POST_URL, payload, auth=test_auth)
        user = collection_submission.collection.provider.get_group('moderator').user_set.first()
        collection_submission.refresh_from_db()
        action = collection_submission.actions.last()

        assert action.trigger == CollectionSubmissionsTriggers.ACCEPT
        assert action.creator == user
        assert action.from_state == CollectionSubmissionStates.PENDING
        assert action.to_state == CollectionSubmissionStates.ACCEPTED
        assert collection_submission.state is CollectionSubmissionStates.ACCEPTED

    def test_POST_reject__writes_action_and_advances_state(self, app, collection_submission, node):
        collection_submission.state_machine.set_state(CollectionSubmissionStates.PENDING)
        collection_submission.save()
        test_auth = configure_test_auth(node, UserRoles.MODERATOR)
        payload = make_payload(collection_submission, trigger=CollectionSubmissionsTriggers.REJECT.db_name)
        app.post_json_api(POST_URL, payload, auth=test_auth)
        user = collection_submission.collection.provider.get_group('moderator').user_set.first()
        collection_submission.refresh_from_db()
        action = collection_submission.actions.last()

        assert action.trigger == CollectionSubmissionsTriggers.REJECT
        assert action.creator == user
        assert action.from_state == CollectionSubmissionStates.PENDING
        assert action.to_state == CollectionSubmissionStates.REJECTED
        assert collection_submission.state is CollectionSubmissionStates.REJECTED

    def test_POST_cancel__writes_action_and_advances_state(self, app, collection_submission, node):
        collection_submission.state_machine.set_state(CollectionSubmissionStates.PENDING)
        collection_submission.save()
        test_auth = configure_test_auth(node, UserRoles.ADMIN_USER)
        payload = make_payload(collection_submission, trigger=CollectionSubmissionsTriggers.CANCEL.db_name)
        app.post_json_api(POST_URL, payload, auth=test_auth)
        collection_submission.refresh_from_db()
        action = collection_submission.actions.last()

        assert action.trigger == CollectionSubmissionsTriggers.CANCEL
        assert action.creator.username == test_auth[0]
        assert action.from_state == CollectionSubmissionStates.PENDING
        assert action.to_state == CollectionSubmissionStates.IN_PROGRESS
        assert collection_submission.state is CollectionSubmissionStates.IN_PROGRESS

    def test_POST_remove__writes_action_and_advances_state(self, app, collection_submission, node):
        collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        collection_submission.save()
        test_auth = configure_test_auth(node, UserRoles.MODERATOR)
        payload = make_payload(collection_submission, trigger=CollectionSubmissionsTriggers.REMOVE.db_name)
        app.post_json_api(POST_URL, payload, auth=test_auth)
        user = collection_submission.collection.provider.get_group('moderator').user_set.first()
        collection_submission.refresh_from_db()
        action = collection_submission.actions.last()

        assert action.trigger == CollectionSubmissionsTriggers.REMOVE
        assert action.creator == user
        assert action.from_state == CollectionSubmissionStates.ACCEPTED
        assert action.to_state == CollectionSubmissionStates.REMOVED
        assert collection_submission.state is CollectionSubmissionStates.REMOVED

    def test_POST_resubmit__writes_action_and_advances_state(self, app, collection_submission, node):
        collection_submission.state_machine.set_state(CollectionSubmissionStates.REMOVED)
        collection_submission.save()
        test_auth = configure_test_auth(node, UserRoles.ADMIN_USER)
        payload = make_payload(collection_submission, trigger=CollectionSubmissionsTriggers.RESUBMIT.db_name)
        app.post_json_api(POST_URL, payload, auth=test_auth, expect_errors=True)
        collection_submission.refresh_from_db()
        action = collection_submission.actions.last()

        assert action.trigger == CollectionSubmissionsTriggers.RESUBMIT
        assert action.creator.username == test_auth[0]
        assert action.from_state == CollectionSubmissionStates.REMOVED
        assert action.to_state == CollectionSubmissionStates.PENDING
        assert collection_submission.state is CollectionSubmissionStates.PENDING

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_status_code__deleted_collection_submission(self, app, node, collection_submission, user_role):
        node.deleted = timezone.now()
        node.save()
        test_auth = configure_test_auth(node, user_role)
        resp = app.post_json_api(POST_URL, make_payload(collection_submission), auth=test_auth, expect_errors=True)
        assert resp.status_code == 410

    def test_status_code__private_collection_moderator(self, app, node, collection, collection_submission):
        collection_submission.state_machine.set_state(CollectionSubmissionStates.PENDING)
        collection_submission.save()
        collection.is_public = False
        collection.save()
        test_auth = configure_test_auth(node, UserRoles.MODERATOR)
        resp = app.post_json_api(
            POST_URL,
            make_payload(
                collection_submission,
                trigger=CollectionSubmissionsTriggers.ACCEPT.db_name
            ),
            auth=test_auth,
            expect_errors=True
        )
        assert resp.status_code == 201


@pytest.mark.django_db
class TestCollectionSubmissionsActionsListUnsupportedMethods:

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_cannot_PATCH(self, app, user_role, node, collection_submission, collection_submission_action):
        auth = configure_test_auth(node, user_role)
        resp = app.patch_json_api(POST_URL.format(collection_submission_action._id), auth=auth, expect_errors=True)
        assert resp.status_code == 405

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_cannot_PUT(self, app, user_role, node, collection_submission, collection_submission_action):
        auth = configure_test_auth(node, user_role)
        resp = app.put_json_api(POST_URL.format(collection_submission_action._id), auth=auth, expect_errors=True)
        assert resp.status_code == 405

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_cannot_DELETE(self, app, user_role, node, collection_submission, collection_submission_action):
        auth = configure_test_auth(node, user_role)
        resp = app.delete_json_api(POST_URL.format(collection_submission_action._id), auth=auth, expect_errors=True)
        assert resp.status_code == 405
