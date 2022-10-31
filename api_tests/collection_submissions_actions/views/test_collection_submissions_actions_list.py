import pytest
from api_tests.utils import UserRoles
from osf.utils.workflows import ApprovalStates
from osf_tests.factories import AuthUserFactory
from django.utils import timezone
from osf_tests.factories import NodeFactory, CollectionFactory, CollectionProviderFactory

from osf.migrations import update_provider_auth_groups
from osf.models import CollectionSubmission
from osf.utils.workflows import CollectionSubmissionsTriggers

POST_URL = '/v2/collection_submissions_actions/'


def make_payload(collection_submission, trigger='submit'):
    return {
        'data': {
            'type': 'collection-submissions-actions',
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
        print(provider.get_group('moderator').user_set.all())

    elif user_role in UserRoles.contributor_roles():
        node.add_contributor(user, user_role.get_permissions_string())

    return user.auth


@pytest.mark.django_db
class TestCollectionSubmissionsActionsListPOSTPermissions:

    @pytest.fixture()
    def collection_provider(self):
        collection_provider = CollectionProviderFactory()
        update_provider_auth_groups()
        return collection_provider

    @pytest.fixture()
    def node(self, collection_provider):
        node = NodeFactory(is_public=True)
        node.provider = collection_provider
        node.save()
        return node

    @pytest.fixture()
    def collection(self, collection_provider):
        collection = CollectionFactory()
        collection.provider = collection_provider
        collection.save()
        return collection

    @pytest.fixture()
    def collection_submission(self, node, collection):
        collection_submission = CollectionSubmission(
            guid=node.guids.first(),
            collection=collection,
            creator=node.creator,
        )
        collection_submission.save()
        return collection_submission

    def test_status_code__admin(self, app, node, collection_submission):
        test_auth = configure_test_auth(node, UserRoles.ADMIN_USER)
        resp = app.post_json_api(
            POST_URL,
            make_payload(
                collection_submission=collection_submission,
                trigger=CollectionSubmissionsTriggers.SUBMIT.db_name
            ),
            auth=test_auth,
        )
        assert resp.status_code == 201

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
        collection_submission.to_PENDING_MODERATION()
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
        collection_submission.to_PENDING_MODERATION()
        collection_submission.save()
        test_auth = configure_test_auth(node, user_role)
        resp = app.post_json_api(POST_URL, make_payload(
            collection_submission=collection_submission,
            trigger=moderator_trigger.db_name
        ), auth=test_auth, expect_errors=True)
        expected_code = 403 if user_role is not UserRoles.UNAUTHENTICATED else 401
        assert resp.status_code == expected_code


@pytest.mark.django_db
class TestSubmissionsActionsListPOSTBehavior:

    @pytest.fixture()
    def collection_provider(self):
        collection_provider = CollectionProviderFactory()
        update_provider_auth_groups()
        return collection_provider

    @pytest.fixture()
    def node(self, collection_provider):
        node = NodeFactory(is_public=True)
        node.provider = collection_provider
        node.save()
        return node

    @pytest.fixture()
    def collection(self, collection_provider):
        collection = CollectionFactory()
        collection.provider = collection_provider
        collection.save()
        return collection

    @pytest.fixture()
    def collection_submission(self, node, collection):
        collection_submission = CollectionSubmission(
            guid=node.guids.first(),
            collection=collection,
            creator=node.creator,
        )
        collection_submission.save()
        return collection_submission

    def test_POST_accept__writes_action_and_advances_state(self, app, collection_submission, node):
        collection_submission.to_PENDING_MODERATION()
        collection_submission.save()
        print("????")
        test_auth = configure_test_auth(node, UserRoles.MODERATOR)
        payload = make_payload(collection_submission, trigger=CollectionSubmissionsTriggers.ACCEPT.db_name)
        app.post_json_api(POST_URL, payload, auth=test_auth)
        user = collection_submission.collection.provider.get_group('moderator').user_set.first()
        collection_submission.refresh_from_db()
        action = collection_submission.actions.last()
        print(action)
        print(collection_submission.actions.all())

        assert action.trigger == CollectionSubmissionsTriggers.ACCEPT
        assert action.creator == user
        assert action.from_state == ApprovalStates.PENDING_MODERATION
        assert action.to_state == ApprovalStates.APPROVED
        assert collection_submission.state is ApprovalStates.APPROVED

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_status_code__deleted_collection_submission(self, app, node, collection_submission, user_role):
        node.deleted = timezone.now()
        node.save()
        test_auth = configure_test_auth(node, user_role)
        resp = app.post_json_api(POST_URL, make_payload(collection_submission), auth=test_auth, expect_errors=True)
        assert resp.status_code == 410

@pytest.mark.django_db
class TestSubmissionsActionsListUnsupportedMethods:
    pass
