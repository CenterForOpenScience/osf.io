import pytest
from api_tests.utils import UserRoles
from osf_tests.factories import AuthUserFactory
from osf_tests.factories import NodeFactory, CollectionFactory, CollectionProviderFactory

from osf.migrations import update_provider_auth_groups
from osf.models import CollectionSubmission
from osf.utils.workflows import CollectionSubmissionsTriggers, CollectionSubmissionStates

GET_URL = '/v2/collection_submissions/{}/actions/'


@pytest.fixture()
def collection_provider():
    collection_provider = CollectionProviderFactory()
    update_provider_auth_groups()
    return collection_provider


@pytest.fixture()
def node(collection_provider):
    node = NodeFactory(is_public=True)
    node.save()
    return node


@pytest.fixture()
def collection(collection_provider):
    collection = CollectionFactory(is_public=True)
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


def configure_test_auth(node, user_role):
    if user_role is UserRoles.UNAUTHENTICATED:
        return None

    user = AuthUserFactory()
    if user_role is UserRoles.MODERATOR:
        collection_submission = CollectionSubmission.objects.get(guid=node.guids.first())
        collection_submission.collection.provider.get_group('moderator').user_set.add(user)
    elif user_role in UserRoles.contributor_roles():
        node.add_contributor(user, user_role.get_permissions_string())

    return user.auth


@pytest.mark.django_db
class TestCollectionSubmissionsActionsDetailGETPermissions:
    @pytest.mark.parametrize('user_role', UserRoles)
    def test_status_code__200(self, app, node, user_role, collection_submission):
        test_auth = configure_test_auth(node, user_role)
        resp = app.get(GET_URL.format(collection_submission._id), auth=test_auth, expect_errors=True)
        assert resp.status_code == 200

    @pytest.mark.parametrize('user_role', [UserRoles.UNAUTHENTICATED, UserRoles.NONCONTRIB])
    def test_private_collection_noncontribs(self, app, node, collection, user_role, collection_submission):
        collection.is_public = False
        collection.save()
        test_auth = configure_test_auth(node, user_role)
        resp = app.get(GET_URL.format(collection_submission._id), auth=test_auth, expect_errors=True)
        assert resp.status_code in (401, 403)

    @pytest.mark.parametrize('user_role', UserRoles.excluding(*[UserRoles.UNAUTHENTICATED, UserRoles.NONCONTRIB]))
    def test_private_collection_contribs(self, app, node, collection, user_role, collection_submission):
        collection.is_public = False
        collection.save()
        test_auth = configure_test_auth(node, user_role)
        resp = app.get(GET_URL.format(collection_submission._id), auth=test_auth, expect_errors=True)
        assert resp.status_code == 200


@pytest.mark.django_db
class TestCollectionSubmissionsActionsDetailGETBehavior:
    def test_return_action(self, app, node, collection_submission):
        collection_submission_action = collection_submission.actions.last()
        resp = app.get(GET_URL.format(collection_submission._id), expect_errors=True)
        data = resp.json['data'][0]
        assert data['id'] == collection_submission_action._id
        assert data['attributes']['from_state'] == CollectionSubmissionStates.IN_PROGRESS.db_name
        assert data['attributes']['to_state'] == CollectionSubmissionStates.ACCEPTED.db_name
        assert data['attributes']['trigger'] == CollectionSubmissionsTriggers.SUBMIT.db_name
        assert data['attributes']['comment'] == 'Initial submission action'
        assert data['relationships']['creator']['data']['id'] == collection_submission.creator._id
        assert data['relationships']['collection']['data']['id'] == collection_submission.collection._id
        assert data['relationships']['target']['data']['id'] \
               == f'{collection_submission.guid._id}-{collection_submission.collection._id}'
        assert resp.status_code == 200


@pytest.mark.django_db
class TestCollectionSubmissionsActionsDetailUnsupportedMethods:

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_cannot_PATCH(self, app, user_role, node, collection_submission):
        auth = configure_test_auth(node, user_role)
        resp = app.patch_json_api(GET_URL.format(collection_submission._id), auth=auth, expect_errors=True)
        assert resp.status_code == 405

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_cannot_POST(self, app, user_role, node, collection_submission):
        auth = configure_test_auth(node, user_role)
        resp = app.post_json_api(GET_URL.format(collection_submission._id), auth=auth, expect_errors=True)
        assert resp.status_code == 405

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_cannot_PUT(self, app, user_role, node, collection_submission):
        auth = configure_test_auth(node, user_role)
        resp = app.put_json_api(GET_URL.format(collection_submission._id), auth=auth, expect_errors=True)
        assert resp.status_code == 405

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_cannot_DELETE(self, app, user_role, node, collection_submission):
        auth = configure_test_auth(node, user_role)
        resp = app.delete_json_api(GET_URL.format(collection_submission._id), auth=auth, expect_errors=True)
        assert resp.status_code == 405
