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
    node.provider = collection_provider
    node.save()
    return node


@pytest.fixture()
def collection(collection_provider):
    collection = CollectionFactory()
    collection.is_public = True
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
        from_state='in_progress',
        to_state='unapproved',
        trigger='submit',
        creator=collection_submission.creator,
        comment='test comment'
    )
    return action


def configure_test_auth(node, user_role):
    if user_role is UserRoles.UNAUTHENTICATED:
        return None

    user = AuthUserFactory()
    if user_role is UserRoles.MODERATOR:
        node.provider.get_group('moderator').user_set.add(user)
    elif user_role in UserRoles.contributor_roles():
        node.add_contributor(user, user_role.get_permissions_string())

    return user.auth


@pytest.mark.django_db
class TestCollectionSubmissionsDetailGETPermissions:

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_status_code__200(self, app, node, user_role, collection_submission):
        test_auth = configure_test_auth(node, user_role)
        resp = app.get(GET_URL.format(collection_submission._id), auth=test_auth, expect_errors=True)
        assert resp.status_code == 200

    @pytest.mark.parametrize('user_role', [UserRoles.UNAUTHENTICATED, UserRoles.NONCONTRIB])
    def test_private_collection_non_contrib_unauth(self, app, node, collection_submission, collection, user_role):
        collection.is_public = False
        collection.save()

        test_auth = configure_test_auth(node, user_role)
        resp = app.get(GET_URL.format(collection_submission._id), auth=test_auth, expect_errors=True)
        expected_code = 403 if user_role is not UserRoles.UNAUTHENTICATED else 401
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('user_role', UserRoles.excluding(*[UserRoles.UNAUTHENTICATED, UserRoles.NONCONTRIB]))
    def test_private_collection_contrib_moderator(self, app, node, collection_submission, collection, user_role):
        collection.is_private = False
        collection.save()

        test_auth = configure_test_auth(node, user_role)
        resp = app.get(GET_URL.format(collection_submission._id), auth=test_auth, expect_errors=True)
        assert resp.status_code == 200


@pytest.mark.django_db
class TestCollectionSubmissionsDetailGETBehavior:

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_status_code__200(self, app, node, user_role, collection_submission):
        test_auth = configure_test_auth(node, user_role)
        resp = app.get(GET_URL.format(collection_submission._id), auth=test_auth, expect_errors=True)
        assert resp.status_code == 200
        assert resp.json['data']['id'] == collection_submission._id


@pytest.mark.django_db
class TestCollectionSubmissionsDetailDELETEPermissions:

    @pytest.mark.parametrize('user_role', UserRoles.excluding(*[UserRoles.ADMIN_USER, UserRoles.MODERATOR]))
    def test_status_code__non_admin_moderator(self, app, node, collection_submission, user_role):
        test_auth = configure_test_auth(node, user_role)
        resp = app.delete_json_api(GET_URL.format(collection_submission._id), auth=test_auth, expect_errors=True)
        expected_code = 403 if user_role is not UserRoles.UNAUTHENTICATED else 401
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('user_role', [UserRoles.ADMIN_USER, UserRoles.MODERATOR])
    def test_status_code__admin_moderator(self, app, node, collection_submission, user_role):
        test_auth = configure_test_auth(node, user_role)
        resp = app.delete_json_api(GET_URL.format(collection_submission._id), auth=test_auth, expect_errors=True)
        assert resp.status_code == 204


@pytest.mark.django_db
class TestCollectionSubmissionsDetailDELETEBehavior:

    @pytest.mark.parametrize('user_role', [UserRoles.ADMIN_USER, UserRoles.MODERATOR])
    def test_moderator_remove_from_collection(self, app, node, user_role, collection_submission, collection):
        test_auth = configure_test_auth(node, user_role)
        resp = app.delete_json_api(GET_URL.format(collection_submission._id), auth=test_auth, expect_errors=True)

        assert not CollectionSubmission.load(collection_submission._id)
        assert collection_submission.guid not in collection.guid_links.all()
        assert resp.status_code == 204


@pytest.mark.django_db
class TestCollectionSubmissionsListUnsupportedMethods:

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
