import pytest
from api_tests.utils import UserRoles
from osf_tests.factories import AuthUserFactory
from osf_tests.factories import NodeFactory, CollectionFactory, CollectionProviderFactory

from osf.migrations import update_provider_auth_groups
from osf.models import CollectionSubmission

GET_URL = '/v2/collection_submissions/{}/actions/'


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
class TestCollectionSubmissionsDetailActionsListGETPermissions:

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_status_code__200(self, app, node, user_role, collection_submission, collection_submission_action):
        test_auth = configure_test_auth(node, user_role)
        resp = app.get(GET_URL.format(collection_submission._id), auth=test_auth, expect_errors=True)
        assert resp.status_code == 200


@pytest.mark.django_db
class TestCollectionSubmissionsDetailActionsListGETBehavior:

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_status_code__200(self, app, node, user_role, collection_submission, collection_submission_action):
        test_auth = configure_test_auth(node, user_role)
        resp = app.get(GET_URL.format(collection_submission._id), auth=test_auth, expect_errors=True)
        assert resp.status_code == 200
        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['id'] == collection_submission_action._id