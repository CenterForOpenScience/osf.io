import mock
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
from website.mails import mails
from osf_tests.utils import assert_notification_correctness
from osf.models.collection_submission import mails as collection_submission_mail


@pytest.fixture
def user():
    return AuthUserFactory()


@pytest.fixture()
def moderated_collection_provider():
    collection_provider = CollectionProviderFactory()
    collection_provider.reviews_workflow = 'pre-moderation'
    collection_provider.update_group_permissions()
    collection_provider.save()
    return collection_provider


@pytest.fixture()
def unmoderated_collection_provider():
    collection_provider = CollectionProviderFactory()
    collection_provider.reviews_workflow = 'post-moderation'
    collection_provider.update_group_permissions()
    collection_provider.save()
    return collection_provider


@pytest.fixture()
def semimoderated_collection_provider():
    collection_provider = CollectionProviderFactory()
    collection_provider.reviews_workflow = 'semi-moderation'
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
def semimoderated_collection(semimoderated_collection_provider):
    collection = CollectionFactory()
    collection.provider = semimoderated_collection_provider
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

@pytest.fixture()
def semimoderated_collection_submission(node, semimoderated_collection):
    collection_submission = CollectionSubmission(
        guid=node.guids.first(),
        collection=semimoderated_collection,
        creator=node.creator,
    )
    collection_submission.save()
    assert collection_submission.is_semi_moderated
    return collection_submission


def configure_test_auth(node, user_role, provider=None):
    if user_role is UserRoles.UNAUTHENTICATED:
        return None

    user = AuthUserFactory()
    if user_role is UserRoles.MODERATOR:
        if provider:
            provider.get_group('moderator').user_set.add(user)
        else:
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

    def test_notify_moderated_accepted(self, node, moderated_collection_submission):
        moderator = configure_test_auth(node, UserRoles.MODERATOR)
        send_mail = mails.send_mail
        with mock.patch.object(collection_submission_mail, 'send_mail') as mock_send:
            mock_send.side_effect = send_mail  # implicitly test rendering
            moderated_collection_submission.accept(user=moderator, comment='Test Comment')
            assert mock_send.called
        assert moderated_collection_submission.state == CollectionSubmissionStates.ACCEPTED
        assert_notification_correctness(
            mock_send,
            mails.COLLECTION_SUBMISSION_ACCEPTED(moderated_collection_submission.collection, node),
            {user.username for user in node.contributors.all()}
        )

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

    def test_notify_moderated_rejected(self, node, moderated_collection_submission):
        moderator = configure_test_auth(node, UserRoles.MODERATOR)
        send_mail = mails.send_mail
        with mock.patch.object(collection_submission_mail, 'send_mail') as mock_send:
            mock_send.side_effect = send_mail  # implicitly test rendering
            moderated_collection_submission.reject(user=moderator, comment='Test Comment')
            assert mock_send.called
        assert moderated_collection_submission.state == CollectionSubmissionStates.REJECTED

        assert_notification_correctness(
            mock_send,
            mails.COLLECTION_SUBMISSION_REJECTED(moderated_collection_submission.collection, node),
            {user.username for user in node.contributors.all()}
        )

    @pytest.mark.parametrize('user_role', UserRoles.excluding(*[UserRoles.ADMIN_USER, UserRoles.MODERATOR]))
    def test_remove_fails(self, node, user_role, moderated_collection_submission):
        user = configure_test_auth(node, user_role)
        moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        moderated_collection_submission.save()
        with pytest.raises(PermissionsError):
            moderated_collection_submission.remove(user=user, comment='Test Comment')
        assert moderated_collection_submission.state == CollectionSubmissionStates.ACCEPTED

    @pytest.mark.parametrize('user_role', [UserRoles.ADMIN_USER, UserRoles.MODERATOR])
    def test_remove_success(self, node, user_role, moderated_collection_submission):
        user = configure_test_auth(node, user_role)
        moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        moderated_collection_submission.save()
        moderated_collection_submission.remove(user=user, comment='Test Comment')
        assert moderated_collection_submission.state == CollectionSubmissionStates.REMOVED

    def test_notify_moderated_removed_moderator(self, node, moderated_collection_submission):
        moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        moderator = configure_test_auth(node, UserRoles.MODERATOR)
        send_mail = mails.send_mail
        with mock.patch.object(collection_submission_mail, 'send_mail') as mock_send:
            mock_send.side_effect = send_mail  # implicitly test rendering
            moderated_collection_submission.remove(user=moderator, comment='Test Comment')
            assert mock_send.called
        assert moderated_collection_submission.state == CollectionSubmissionStates.REMOVED

        assert_notification_correctness(
            mock_send,
            mails.COLLECTION_SUBMISSION_REMOVED_MODERATOR(moderated_collection_submission.collection, node),
            {user.username for user in node.contributors.all()}
        )

    def test_notify_moderated_removed_admin(self, node, moderated_collection_submission):
        moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        moderator = configure_test_auth(node, UserRoles.ADMIN_USER)
        send_mail = mails.send_mail
        with mock.patch.object(collection_submission_mail, 'send_mail') as mock_send:
            mock_send.side_effect = send_mail  # implicitly test rendering
            moderated_collection_submission.remove(user=moderator, comment='Test Comment')
            assert mock_send.called
        assert moderated_collection_submission.state == CollectionSubmissionStates.REMOVED

        assert_notification_correctness(
            mock_send,
            mails.COLLECTION_SUBMISSION_REMOVED_ADMIN(moderated_collection_submission.collection, node),
            {user.username for user in node.contributors.all()}
        )

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

    @pytest.mark.parametrize('user_role', UserRoles.excluding(UserRoles.ADMIN_USER))
    def test_remove_fails(self, node, user_role, unmoderated_collection_submission):
        user = configure_test_auth(node, user_role)
        unmoderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        unmoderated_collection_submission.save()
        with pytest.raises(PermissionsError):
            unmoderated_collection_submission.remove(user=user, comment='Test Comment')
        assert unmoderated_collection_submission.state == CollectionSubmissionStates.ACCEPTED

    def test_remove_success(self, node, unmoderated_collection_submission):
        user = configure_test_auth(node, UserRoles.ADMIN_USER)
        unmoderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        unmoderated_collection_submission.save()
        unmoderated_collection_submission.remove(user=user, comment='Test Comment')
        assert unmoderated_collection_submission.state == CollectionSubmissionStates.REMOVED

    def test_notify_moderated_removed_admin(self, node, unmoderated_collection_submission):
        unmoderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        moderator = configure_test_auth(node, UserRoles.ADMIN_USER)
        send_mail = mails.send_mail
        with mock.patch.object(collection_submission_mail, 'send_mail') as mock_send:
            mock_send.side_effect = send_mail  # implicitly test rendering
            unmoderated_collection_submission.remove(user=moderator, comment='Test Comment')
            assert mock_send.called
        assert unmoderated_collection_submission.state == CollectionSubmissionStates.REMOVED

        assert_notification_correctness(
            mock_send,
            mails.COLLECTION_SUBMISSION_REMOVED_ADMIN(unmoderated_collection_submission.collection, node),
            {user.username for user in node.contributors.all()}
        )

    @pytest.mark.parametrize('user_role', UserRoles.excluding(
        *[UserRoles.MODERATOR, UserRoles.UNAUTHENTICATED, UserRoles.NONCONTRIB]
    ))
    def test_resubmit_success(self, node, user_role, unmoderated_collection_submission):
        user = configure_test_auth(node, user_role)
        unmoderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.REMOVED)
        unmoderated_collection_submission.save()
        unmoderated_collection_submission.resubmit(user=user, comment='Test Comment')
        assert unmoderated_collection_submission.state == CollectionSubmissionStates.ACCEPTED

    @pytest.mark.parametrize('user_role', [UserRoles.MODERATOR, UserRoles.UNAUTHENTICATED, UserRoles.NONCONTRIB])
    def test_resubmit_fails(self, node, user_role, unmoderated_collection_submission):
        user = configure_test_auth(node, user_role)
        unmoderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.REMOVED)
        unmoderated_collection_submission.save()
        with pytest.raises(PermissionsError):
            unmoderated_collection_submission.resubmit(user=user, comment='Test Comment')
        assert unmoderated_collection_submission.state == CollectionSubmissionStates.REMOVED


@pytest.mark.django_db
class TestSemimoderatedCollectionSubmission:

    @pytest.mark.parametrize('user_role', UserRoles.excluding(UserRoles.MODERATOR))
    def test_semimoderated_submit(self, user_role, node, semimoderated_collection):
        configure_test_auth(node, user_role)
        collection_submission = CollectionSubmission(
            guid=node.guids.first(),
            collection=semimoderated_collection,
            creator=node.creator,
        )

        collection_submission.save()
        assert collection_submission.is_semi_moderated
        assert not collection_submission.is_collection_moderator_admin_owned
        # .submit on post_save
        assert collection_submission.state == CollectionSubmissionStates.PENDING

    @pytest.mark.parametrize('user_role', [UserRoles.MODERATOR])
    def test_semimoderated_submit_moderator(self, user_role, node, semimoderated_collection):
        user = configure_test_auth(node, user_role, provider=semimoderated_collection.provider)
        node.add_contributor(user)
        collection_submission = CollectionSubmission(
            guid=node.guids.first(),
            collection=semimoderated_collection,
            creator=node.creator,
        )
        collection_submission.save()
        assert collection_submission.is_semi_moderated
        assert collection_submission.is_collection_moderator_admin_owned
        assert collection_submission.state == CollectionSubmissionStates.ACCEPTED

    @pytest.mark.parametrize('user_role', [UserRoles.UNAUTHENTICATED, UserRoles.NONCONTRIB])
    def test_accept_fails(self, user_role, semimoderated_collection_submission):
        user = configure_test_auth(node, user_role)
        with pytest.raises(PermissionsError):
            semimoderated_collection_submission.accept(user=user, comment='Test Comment')
        assert semimoderated_collection_submission.state == CollectionSubmissionStates.PENDING

    def test_accept_success(self, node, semimoderated_collection_submission):
        moderator = configure_test_auth(node, UserRoles.MODERATOR)
        semimoderated_collection_submission.accept(user=moderator, comment='Test Comment')
        assert semimoderated_collection_submission.state == CollectionSubmissionStates.ACCEPTED

    def test_notify_moderated_accepted(self, node, semimoderated_collection_submission):
        moderator = configure_test_auth(node, UserRoles.MODERATOR)
        send_mail = mails.send_mail
        with mock.patch.object(collection_submission_mail, 'send_mail') as mock_send:
            mock_send.side_effect = send_mail  # implicitly test rendering
            semimoderated_collection_submission.accept(user=moderator, comment='Test Comment')
            assert mock_send.called
        assert semimoderated_collection_submission.state == CollectionSubmissionStates.ACCEPTED

        assert_notification_correctness(
            mock_send,
            mails.COLLECTION_SUBMISSION_ACCEPTED,
            {user.username for user in node.contributors.all()}
        )

    @pytest.mark.parametrize('user_role', [UserRoles.UNAUTHENTICATED, UserRoles.NONCONTRIB])
    def test_reject_fails(self, node, user_role, semimoderated_collection_submission):
        user = configure_test_auth(node, user_role)
        with pytest.raises(PermissionsError):
            semimoderated_collection_submission.reject(user=user, comment='Test Comment')
        assert semimoderated_collection_submission.state == CollectionSubmissionStates.PENDING

    def test_reject_success(self, node, semimoderated_collection_submission):
        moderator = configure_test_auth(node, UserRoles.MODERATOR)
        semimoderated_collection_submission.reject(user=moderator, comment='Test Comment')
        assert semimoderated_collection_submission.state == CollectionSubmissionStates.REJECTED

    def test_notify_moderated_rejected(self, node, semimoderated_collection_submission):
        moderator = configure_test_auth(node, UserRoles.MODERATOR)
        send_mail = mails.send_mail
        with mock.patch.object(collection_submission_mail, 'send_mail') as mock_send:
            mock_send.side_effect = send_mail  # implicitly test rendering
            semimoderated_collection_submission.reject(user=moderator, comment='Test Comment')
            assert mock_send.called
        assert semimoderated_collection_submission.state == CollectionSubmissionStates.REJECTED

        assert_notification_correctness(
            mock_send,
            mails.COLLECTION_SUBMISSION_REJECTED,
            {user.username for user in node.contributors.all()}
        )

    @pytest.mark.parametrize('user_role', UserRoles.excluding(*[UserRoles.ADMIN_USER, UserRoles.MODERATOR]))
    def test_remove_fails(self, node, user_role, semimoderated_collection_submission):
        user = configure_test_auth(node, user_role)
        semimoderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        semimoderated_collection_submission.save()
        with pytest.raises(PermissionsError):
            semimoderated_collection_submission.remove(user=user, comment='Test Comment')
        assert semimoderated_collection_submission.state == CollectionSubmissionStates.ACCEPTED

    @pytest.mark.parametrize('user_role', [UserRoles.ADMIN_USER, UserRoles.MODERATOR])
    def test_remove_success(self, node, user_role, semimoderated_collection_submission):
        user = configure_test_auth(node, user_role)
        semimoderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        semimoderated_collection_submission.save()
        semimoderated_collection_submission.remove(user=user, comment='Test Comment')
        assert semimoderated_collection_submission.state == CollectionSubmissionStates.REMOVED

    def test_notify_moderated_removed_moderator(self, node, semimoderated_collection_submission):
        semimoderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        moderator = configure_test_auth(node, UserRoles.MODERATOR)
        send_mail = mails.send_mail
        with mock.patch.object(collection_submission_mail, 'send_mail') as mock_send:
            mock_send.side_effect = send_mail  # implicitly test rendering
            semimoderated_collection_submission.remove(user=moderator, comment='Test Comment')
            assert mock_send.called
        assert semimoderated_collection_submission.state == CollectionSubmissionStates.REMOVED

        assert_notification_correctness(
            mock_send,
            mails.COLLECTION_SUBMISSION_REMOVED_MODERATOR,
            {user.username for user in node.contributors.all()}
        )

    def test_notify_moderated_removed_admin(self, node, semimoderated_collection_submission):
        semimoderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        moderator = configure_test_auth(node, UserRoles.ADMIN_USER)
        send_mail = mails.send_mail
        with mock.patch.object(collection_submission_mail, 'send_mail') as mock_send:
            mock_send.side_effect = send_mail  # implicitly test rendering
            semimoderated_collection_submission.remove(user=moderator, comment='Test Comment')
            assert mock_send.called
        assert semimoderated_collection_submission.state == CollectionSubmissionStates.REMOVED

        assert_notification_correctness(
            mock_send,
            mails.COLLECTION_SUBMISSION_REMOVED_ADMIN,
            {user.username for user in node.contributors.all()}
        )

    def test_resubmit_success(self, node, semimoderated_collection_submission):
        user = configure_test_auth(node, UserRoles.ADMIN_USER)
        semimoderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.REMOVED)
        semimoderated_collection_submission.save()
        semimoderated_collection_submission.resubmit(user=user, comment='Test Comment')
        assert semimoderated_collection_submission.state == CollectionSubmissionStates.PENDING

    @pytest.mark.parametrize('user_role', UserRoles.excluding(UserRoles.ADMIN_USER))
    def test_resubmit_fails(self, node, user_role, semimoderated_collection_submission):
        user = configure_test_auth(node, user_role)
        semimoderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.REMOVED)
        semimoderated_collection_submission.save()
        with pytest.raises(PermissionsError):
            semimoderated_collection_submission.resubmit(user=user, comment='Test Comment')
        assert semimoderated_collection_submission.state == CollectionSubmissionStates.REMOVED
