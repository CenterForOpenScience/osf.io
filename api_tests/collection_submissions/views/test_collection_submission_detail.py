import pytest
from api_tests.utils import UserRoles
from osf_tests.factories import AuthUserFactory
from osf_tests.factories import NodeFactory, CollectionFactory, CollectionProviderFactory

from osf.migrations import update_provider_auth_groups
from osf.models import CollectionSubmission

GET_URL = '/v2/collection_submissions/{}/'


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
class TestCollectionSubmissionDetailGETPermissions:
    @pytest.mark.parametrize('user_role', UserRoles)
    def test_status_code__200(self, app, node, user_role, collection_submission):
        test_auth = configure_test_auth(node, user_role)
        resp = app.get(GET_URL.format(collection_submission._id), auth=test_auth, expect_errors=True)
        assert resp.status_code == 200

    @pytest.mark.parametrize('user_role', UserRoles.excluding(UserRoles.MODERATOR))
    def test_private_collection_non_moderators(self, app, node, collection, user_role, collection_submission):
        collection.is_public = False
        collection.save()
        test_auth = configure_test_auth(node, user_role)
        resp = app.get(GET_URL.format(collection_submission._id), auth=test_auth, expect_errors=True)
        assert resp.status_code in (401, 403)

    def test_private_collection_moderators(self, app, node, collection, collection_submission):
        collection.is_public = False
        collection.save()
        test_auth = configure_test_auth(node, UserRoles.MODERATOR)
        resp = app.get(GET_URL.format(collection_submission._id), auth=test_auth, expect_errors=True)
        assert resp.status_code == 200


@pytest.mark.django_db
class TestCollectionSubmissionsActionsDetailGETBehavior:
    def test_return_collection_submission(self, app, node, collection_submission):
        resp = app.get(GET_URL.format(collection_submission._id), expect_errors=True)
        assert resp.json['data']['id'] == collection_submission.collection._id
        assert resp.json['data']['relationships']['creator']['data']['id'] == collection_submission.creator._id
        assert resp.json['data']['relationships']['collection']['data']['id'] == collection_submission.collection._id
        assert resp.json['data']['relationships']['target']['data']['id'] \
               == f'{collection_submission.guid._id}-{collection_submission.collection._id}'
        assert resp.status_code == 200


@pytest.mark.django_db
class TestCollectionSubmissionDetailDELETEBehavior:
    def test_delete_collection_submission(self, app, node, collection_submission):
        test_auth = configure_test_auth(node, UserRoles.ADMIN_USER)
        resp = app.delete_json_api(GET_URL.format(collection_submission._id), auth=test_auth, expect_errors=True)
        assert resp.status_code == 204
        assert CollectionSubmission.load(collection_submission._id) is None


@pytest.mark.django_db
class TestCollectionSubmissionDetailDELETEPermissions:
    def test_delete_collection_submission_admin(self, app, node, collection_submission):
        test_auth = configure_test_auth(node, UserRoles.ADMIN_USER)
        resp = app.delete_json_api(GET_URL.format(collection_submission._id), auth=test_auth, expect_errors=True)
        assert resp.status_code == 204

    @pytest.mark.parametrize('user_role', UserRoles.excluding(UserRoles.ADMIN_USER))
    def test_delete_collection_submission_non_admin(self, app, node, collection_submission, user_role):
        test_auth = configure_test_auth(node, user_role)
        resp = app.delete_json_api(GET_URL.format(collection_submission._id), auth=test_auth, expect_errors=True)
        expected_status_code = 403 if test_auth else 401
        assert resp.status_code == expected_status_code


@pytest.mark.django_db
class TestCollectionSubmissionsDetailUnsupportedMethods:
    pass
