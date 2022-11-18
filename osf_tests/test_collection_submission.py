import pytest

from osf_tests.factories import (
    AuthUserFactory,
)

from transitions import MachineError

from osf_tests.factories import NodeFactory, CollectionFactory, CollectionProviderFactory

from osf.models import CollectionSubmission
from osf.utils.workflows import CollectionSubmissionStates
from framework.exceptions import PermissionsError
from api_tests.utils import UserRoles

POST_URL = '/v2/collection_submissions_actions/'


@pytest.fixture
def user():
    return AuthUserFactory()


@pytest.fixture()
def moderated_collection_provider():
    collection_provider = CollectionProviderFactory()
    collection_provider.reviews_workflow = 'post-moderation'
    collection_provider.update_group_permissions()
    collection_provider.save()
    return collection_provider


@pytest.fixture()
def unmoderated_collection_provider():
    collection_provider = CollectionProviderFactory()
    collection_provider.reviews_workflow = 'pre-moderation'
    collection_provider.update_group_permissions()
    collection_provider.save()
    return collection_provider


@pytest.fixture()
def node(moderated_collection_provider):
    node = NodeFactory(is_public=True)
    node.provider = moderated_collection_provider
    node.save()
    return node


@pytest.fixture()
def admin(node):
    return node.creator


@pytest.fixture()
def moderated_collection(moderated_collection_provider):
    collection = CollectionFactory()
    collection.provider = moderated_collection_provider
    collection.save()
    return collection


@pytest.fixture()
def unmoderated_collection(unmoderated_collection_provider):
    collection = CollectionFactory()
    collection.provider = unmoderated_collection_provider
    collection.save()
    return collection


@pytest.fixture()
def moderated_collection_submission(node, moderated_collection):
    collection_submission = CollectionSubmission(
        guid=node.guids.first(),
        collection=moderated_collection,
        creator=node.creator,
    )
    collection_submission.save()
    assert collection_submission.is_moderated
    return collection_submission


@pytest.fixture()
def unmoderated_collection_submission(node, unmoderated_collection):
    collection_submission = CollectionSubmission(
        guid=node.guids.first(),
        collection=unmoderated_collection,
        creator=node.creator,
    )
    collection_submission.save()
    assert not collection_submission.is_moderated
    return collection_submission


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

    return user


@pytest.mark.django_db
class TestModeratedCollectionSubmission:

    def test_submit(self, moderated_collection_submission):
        # .submit on post_save
        assert moderated_collection_submission.state == CollectionSubmissionStates.PENDING

    @pytest.mark.parametrize('user_role', [UserRoles.UNAUTHENTICATED, UserRoles.NONCONTRIB])
    def test_accept_fails(self, user_role, moderated_collection_submission):
        user = configure_test_auth(node, user_role)
        with pytest.raises(PermissionsError):
            moderated_collection_submission.accept(user=user, comment='Test Comment')
        assert moderated_collection_submission.state == CollectionSubmissionStates.PENDING

    def test_accept_success(self, node, moderated_collection_submission):
        moderator = configure_test_auth(node, UserRoles.MODERATOR)
        moderated_collection_submission.accept(user=moderator, comment='Test Comment')
        assert moderated_collection_submission.state == CollectionSubmissionStates.ACCEPTED

    @pytest.mark.parametrize('user_role', [UserRoles.UNAUTHENTICATED, UserRoles.NONCONTRIB])
    def test_reject_fails(self, node, user_role, moderated_collection_submission):
        user = configure_test_auth(node, user_role)
        with pytest.raises(PermissionsError):
            moderated_collection_submission.reject(user=user, comment='Test Comment')
        assert moderated_collection_submission.state == CollectionSubmissionStates.PENDING

    def test_reject_success(self, node, moderated_collection_submission):
        moderator = configure_test_auth(node, UserRoles.MODERATOR)
        moderated_collection_submission.reject(user=moderator, comment='Test Comment')
        assert moderated_collection_submission.state == CollectionSubmissionStates.REJECTED

    @pytest.mark.parametrize('user_role', [UserRoles.ADMIN_USER, UserRoles.MODERATOR])
    def test_remove_success(self, node, user_role, moderated_collection_submission):
        user = configure_test_auth(node, user_role)
        moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        moderated_collection_submission.save()
        moderated_collection_submission.remove(user=user, comment='Test Comment')
        assert moderated_collection_submission.state == CollectionSubmissionStates.REMOVED

    @pytest.mark.parametrize('user_role', UserRoles.excluding(*[UserRoles.ADMIN_USER, UserRoles.MODERATOR]))
    def test_remove_fails(self, node, user_role, moderated_collection_submission):
        user = configure_test_auth(node, user_role)
        moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        moderated_collection_submission.save()
        with pytest.raises(PermissionsError):
            moderated_collection_submission.remove(user=user, comment='Test Comment')
        assert moderated_collection_submission.state == CollectionSubmissionStates.ACCEPTED

    def test_resubmit_success(self, node, moderated_collection_submission):
        user = configure_test_auth(node, UserRoles.ADMIN_USER)
        moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.REMOVED)
        moderated_collection_submission.save()
        moderated_collection_submission.resubmit(user=user, comment='Test Comment')
        assert moderated_collection_submission.state == CollectionSubmissionStates.PENDING

    @pytest.mark.parametrize('user_role', UserRoles.excluding(UserRoles.ADMIN_USER))
    def test_resubmit_fails(self, node, user_role, moderated_collection_submission):
        user = configure_test_auth(node, user_role)
        moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.REMOVED)
        moderated_collection_submission.save()
        with pytest.raises(PermissionsError):
            moderated_collection_submission.resubmit(user=user, comment='Test Comment')
        assert moderated_collection_submission.state == CollectionSubmissionStates.REMOVED


@pytest.mark.django_db
class TestUnmoderatedCollectionSubmission:

    def test_moderated_submit(self, unmoderated_collection_submission):
        # .submit on post_save
        assert unmoderated_collection_submission.state == CollectionSubmissionStates.ACCEPTED

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_accept_fails(self, node, user_role, unmoderated_collection_submission):
        user = configure_test_auth(node, user_role)
        with pytest.raises(MachineError):
            unmoderated_collection_submission.accept(user=user, comment='Test Comment')
        assert unmoderated_collection_submission.state == CollectionSubmissionStates.ACCEPTED

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_reject_fails(self, node, user_role, unmoderated_collection_submission):
        user = configure_test_auth(node, user_role)
        with pytest.raises(MachineError):
            unmoderated_collection_submission.reject(user=user, comment='Test Comment')
        assert unmoderated_collection_submission.state == CollectionSubmissionStates.ACCEPTED

    @pytest.mark.parametrize('user_role', [UserRoles.ADMIN_USER])
    def test_remove_success(self, node, user_role, unmoderated_collection_submission):
        user = configure_test_auth(node, user_role)
        unmoderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        unmoderated_collection_submission.save()
        unmoderated_collection_submission.remove(user=user, comment='Test Comment')
        assert unmoderated_collection_submission.state == CollectionSubmissionStates.REMOVED

    @pytest.mark.parametrize('user_role', UserRoles.excluding(UserRoles.ADMIN_USER))
    def test_remove_fails(self, node, user_role, unmoderated_collection_submission):
        user = configure_test_auth(node, user_role)
        unmoderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        unmoderated_collection_submission.save()
        with pytest.raises(PermissionsError):
            unmoderated_collection_submission.remove(user=user, comment='Test Comment')
        assert unmoderated_collection_submission.state == CollectionSubmissionStates.ACCEPTED

    def test_resubmit_success(self, node, unmoderated_collection_submission):
        user = configure_test_auth(node, UserRoles.ADMIN_USER)
        unmoderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.REMOVED)
        unmoderated_collection_submission.save()
        unmoderated_collection_submission.resubmit(user=user, comment='Test Comment')
        assert unmoderated_collection_submission.state == CollectionSubmissionStates.ACCEPTED

    @pytest.mark.parametrize('user_role', UserRoles.excluding(UserRoles.ADMIN_USER))
    def test_resubmit_fails(self, node, user_role, unmoderated_collection_submission):
        user = configure_test_auth(node, user_role)
        unmoderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.REMOVED)
        unmoderated_collection_submission.save()
        with pytest.raises(PermissionsError):
            unmoderated_collection_submission.resubmit(user=user, comment='Test Comment')
        assert unmoderated_collection_submission.state == CollectionSubmissionStates.REMOVED

