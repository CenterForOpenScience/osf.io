from unittest import mock
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
from osf.management.commands.populate_collection_provider_notification_subscriptions import populate_collection_provider_notification_subscriptions
from django.utils import timezone

@pytest.fixture
def user():
    return AuthUserFactory()


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
def unmoderated_collection_provider():
    collection_provider = CollectionProviderFactory()
    collection_provider.reviews_workflow = 'post-moderation'
    collection_provider.update_group_permissions()
    collection_provider.save()
    return collection_provider


@pytest.fixture()
def hybrid_moderated_collection_provider():
    collection_provider = CollectionProviderFactory()
    collection_provider.reviews_workflow = 'hybrid-moderation'
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
def hybrid_moderated_collection(hybrid_moderated_collection_provider):
    collection = CollectionFactory()
    collection.provider = hybrid_moderated_collection_provider
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
def hybrid_moderated_collection_submission(node, hybrid_moderated_collection):
    collection_submission = CollectionSubmission(
        guid=node.guids.first(),
        collection=hybrid_moderated_collection,
        creator=node.creator,
    )
    collection_submission.save()
    assert collection_submission.is_hybrid_moderated
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

    MOCK_NOW = timezone.now()

    @pytest.fixture(autouse=True)
    def setup(self):
        populate_collection_provider_notification_subscriptions()
        with mock.patch('osf.utils.machines.timezone.now', return_value=self.MOCK_NOW):
            yield

    def test_submit(self, moderated_collection_submission):
        # .submit on post_save
        assert moderated_collection_submission.state == CollectionSubmissionStates.PENDING

    def test_notify_contributors_pending(self, node, moderated_collection):
        send_mail = mails.send_mail
        with mock.patch.object(collection_submission_mail, 'send_mail') as mock_send:
            mock_send.side_effect = send_mail  # implicitly test rendering
            collection_submission = CollectionSubmission(
                guid=node.guids.first(),
                collection=moderated_collection,
                creator=node.creator,
            )
            collection_submission.save()
            assert mock_send.called
        assert collection_submission.state == CollectionSubmissionStates.PENDING
        assert_notification_correctness(
            mock_send,
            mails.COLLECTION_SUBMISSION_SUBMITTED(collection_submission.creator, node),
            {user.username for user in node.contributors.all()}
        )

    def test_notify_moderators_pending(self, node, moderated_collection):
        from website.notifications import emails
        store_emails = emails.store_emails
        with mock.patch('website.notifications.emails.store_emails') as mock_store_emails:
            mock_store_emails.side_effect = store_emails  # implicitly test rendering
            collection_submission = CollectionSubmission(
                guid=node.guids.first(),
                collection=moderated_collection,
                creator=node.creator,
            )
            populate_collection_provider_notification_subscriptions()
            collection_submission.save()
            assert mock_store_emails.called
        assert collection_submission.state == CollectionSubmissionStates.PENDING
        email_call = mock_store_emails.call_args_list[0][0]
        moderator = moderated_collection.moderators.get()
        assert email_call == (
            [moderator._id],
            'email_transactional',
            'new_pending_submissions',
            collection_submission.creator,
            node,
            self.MOCK_NOW,
        )

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

    @pytest.mark.parametrize('user_role', UserRoles.excluding(UserRoles.ADMIN_USER))
    def test_cancel_fails(self, node, user_role, moderated_collection_submission):
        user = configure_test_auth(node, user_role)
        moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.PENDING)
        moderated_collection_submission.save()
        with pytest.raises(PermissionsError):
            moderated_collection_submission.cancel(user=user, comment='Test Comment')
        assert moderated_collection_submission.state == CollectionSubmissionStates.PENDING

    def test_cancel_succeeds(self, node, moderated_collection_submission):
        user = configure_test_auth(node, UserRoles.ADMIN_USER)
        moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.PENDING)
        moderated_collection_submission.save()
        moderated_collection_submission.cancel(user=user, comment='Test Comment')
        assert moderated_collection_submission.state == CollectionSubmissionStates.IN_PROGRESS


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

    @pytest.mark.parametrize('user_role', UserRoles.excluding(*[UserRoles.ADMIN_USER, UserRoles.MODERATOR]))
    def test_remove_fails(self, node, user_role, unmoderated_collection_submission):
        user = configure_test_auth(node, user_role)
        unmoderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        unmoderated_collection_submission.save()
        with pytest.raises(PermissionsError):
            unmoderated_collection_submission.remove(user=user, comment='Test Comment')
        assert unmoderated_collection_submission.state == CollectionSubmissionStates.ACCEPTED

    @pytest.mark.parametrize('user_role', [UserRoles.ADMIN_USER, UserRoles.MODERATOR])
    def test_remove_success(self, user_role, node, unmoderated_collection_submission):
        user = configure_test_auth(node, user_role)
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

    @pytest.mark.parametrize('user_role', UserRoles.excluding(UserRoles.ADMIN_USER))
    def test_cancel_fails(self, node, user_role, unmoderated_collection_submission):
        user = configure_test_auth(node, user_role)
        unmoderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.PENDING)
        unmoderated_collection_submission.save()
        with pytest.raises(PermissionsError):
            unmoderated_collection_submission.cancel(user=user, comment='Test Comment')
        assert unmoderated_collection_submission.state == CollectionSubmissionStates.PENDING

    def test_cancel_succeeds(self, node, unmoderated_collection_submission):
        user = configure_test_auth(node, UserRoles.ADMIN_USER)
        unmoderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.PENDING)
        unmoderated_collection_submission.save()
        unmoderated_collection_submission.cancel(user=user, comment='Test Comment')
        assert unmoderated_collection_submission.state == CollectionSubmissionStates.IN_PROGRESS


@pytest.mark.django_db
class TestHybridModeratedCollectionSubmission:

    @pytest.mark.parametrize('user_role', UserRoles.excluding(UserRoles.MODERATOR))
    def test_hybrid_submit(self, user_role, node, hybrid_moderated_collection):
        configure_test_auth(node, user_role)
        collection_submission = CollectionSubmission(
            guid=node.guids.first(),
            collection=hybrid_moderated_collection,
            creator=node.creator,
        )

        collection_submission.save()
        assert collection_submission.is_hybrid_moderated
        # .submit on post_save
        assert collection_submission.state == CollectionSubmissionStates.PENDING

    @pytest.mark.parametrize('user_role', [UserRoles.MODERATOR])
    def test_hybrid_submit_moderator_not_submitted(self, user_role, node, hybrid_moderated_collection):
        configure_test_auth(node, user_role, provider=hybrid_moderated_collection.provider)
        not_admin_moderator = AuthUserFactory()
        node.add_contributor(not_admin_moderator)
        collection_submission = CollectionSubmission(
            guid=node.guids.first(),
            collection=hybrid_moderated_collection,
            creator=not_admin_moderator,
        )
        collection_submission.save()
        assert collection_submission.is_hybrid_moderated
        assert collection_submission.state == CollectionSubmissionStates.PENDING

    @pytest.mark.parametrize('user_role', [UserRoles.MODERATOR])
    def test_hybrid_submit_moderator_submitted(self, user_role, node, hybrid_moderated_collection):
        user = configure_test_auth(node, user_role, provider=hybrid_moderated_collection.provider)
        node.add_contributor(user)
        collection_submission = CollectionSubmission(
            guid=node.guids.first(),
            collection=hybrid_moderated_collection,
            creator=user,
        )
        collection_submission.save()
        assert collection_submission.is_hybrid_moderated
        assert collection_submission.state == CollectionSubmissionStates.ACCEPTED

    @pytest.mark.parametrize('user_role', [UserRoles.UNAUTHENTICATED, UserRoles.NONCONTRIB])
    def test_accept_fails(self, user_role, hybrid_moderated_collection_submission):
        user = configure_test_auth(node, user_role)
        with pytest.raises(PermissionsError):
            hybrid_moderated_collection_submission.accept(user=user, comment='Test Comment')
        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.PENDING

    def test_accept_success(self, node, hybrid_moderated_collection_submission):
        moderator = configure_test_auth(node, UserRoles.MODERATOR)
        hybrid_moderated_collection_submission.accept(user=moderator, comment='Test Comment')
        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.ACCEPTED

    def test_notify_moderated_accepted(self, node, hybrid_moderated_collection_submission):
        moderator = configure_test_auth(node, UserRoles.MODERATOR)
        send_mail = mails.send_mail
        with mock.patch.object(collection_submission_mail, 'send_mail') as mock_send:
            mock_send.side_effect = send_mail  # implicitly test rendering
            hybrid_moderated_collection_submission.accept(user=moderator, comment='Test Comment')
            assert mock_send.called
        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.ACCEPTED

        assert_notification_correctness(
            mock_send,
            mails.COLLECTION_SUBMISSION_ACCEPTED(hybrid_moderated_collection_submission.collection, node),
            {user.username for user in node.contributors.all()}
        )

    @pytest.mark.parametrize('user_role', [UserRoles.UNAUTHENTICATED, UserRoles.NONCONTRIB])
    def test_reject_fails(self, node, user_role, hybrid_moderated_collection_submission):
        user = configure_test_auth(node, user_role)
        with pytest.raises(PermissionsError):
            hybrid_moderated_collection_submission.reject(user=user, comment='Test Comment')
        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.PENDING

    def test_reject_success(self, node, hybrid_moderated_collection_submission):
        moderator = configure_test_auth(node, UserRoles.MODERATOR)
        hybrid_moderated_collection_submission.reject(user=moderator, comment='Test Comment')
        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.REJECTED

    def test_notify_moderated_rejected(self, node, hybrid_moderated_collection_submission):
        moderator = configure_test_auth(node, UserRoles.MODERATOR)
        send_mail = mails.send_mail
        with mock.patch.object(collection_submission_mail, 'send_mail') as mock_send:
            mock_send.side_effect = send_mail  # implicitly test rendering
            hybrid_moderated_collection_submission.reject(user=moderator, comment='Test Comment')
            assert mock_send.called
        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.REJECTED

        assert_notification_correctness(
            mock_send,
            mails.COLLECTION_SUBMISSION_REJECTED(hybrid_moderated_collection_submission.collection, node),
            {user.username for user in node.contributors.all()}
        )

    @pytest.mark.parametrize('user_role', UserRoles.excluding(*[UserRoles.ADMIN_USER, UserRoles.MODERATOR]))
    def test_remove_fails(self, node, user_role, hybrid_moderated_collection_submission):
        user = configure_test_auth(node, user_role)
        hybrid_moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        hybrid_moderated_collection_submission.save()
        with pytest.raises(PermissionsError):
            hybrid_moderated_collection_submission.remove(user=user, comment='Test Comment')
        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.ACCEPTED

    @pytest.mark.parametrize('user_role', [UserRoles.ADMIN_USER, UserRoles.MODERATOR])
    def test_remove_success(self, node, user_role, hybrid_moderated_collection_submission):
        user = configure_test_auth(node, user_role)
        hybrid_moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        hybrid_moderated_collection_submission.save()
        hybrid_moderated_collection_submission.remove(user=user, comment='Test Comment')
        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.REMOVED

    def test_notify_moderated_removed_moderator(self, node, hybrid_moderated_collection_submission):
        hybrid_moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        moderator = configure_test_auth(node, UserRoles.MODERATOR)
        send_mail = mails.send_mail
        with mock.patch.object(collection_submission_mail, 'send_mail') as mock_send:
            mock_send.side_effect = send_mail  # implicitly test rendering
            hybrid_moderated_collection_submission.remove(user=moderator, comment='Test Comment')
            assert mock_send.called
        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.REMOVED

        assert_notification_correctness(
            mock_send,
            mails.COLLECTION_SUBMISSION_REMOVED_MODERATOR(hybrid_moderated_collection_submission.collection, node),
            {user.username for user in node.contributors.all()}
        )

    def test_notify_moderated_removed_admin(self, node, hybrid_moderated_collection_submission):
        hybrid_moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        moderator = configure_test_auth(node, UserRoles.ADMIN_USER)
        send_mail = mails.send_mail
        with mock.patch.object(collection_submission_mail, 'send_mail') as mock_send:
            mock_send.side_effect = send_mail  # implicitly test rendering
            hybrid_moderated_collection_submission.remove(user=moderator, comment='Test Comment')
            assert mock_send.called
        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.REMOVED

        assert_notification_correctness(
            mock_send,
            mails.COLLECTION_SUBMISSION_REMOVED_ADMIN(hybrid_moderated_collection_submission.collection, node),
            {user.username for user in node.contributors.all()}
        )

    def test_resubmit_success(self, node, hybrid_moderated_collection_submission):
        user = configure_test_auth(node, UserRoles.ADMIN_USER)
        hybrid_moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.REMOVED)
        hybrid_moderated_collection_submission.save()
        hybrid_moderated_collection_submission.resubmit(user=user, comment='Test Comment')
        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.PENDING

    @pytest.mark.parametrize('user_role', UserRoles.excluding(UserRoles.ADMIN_USER))
    def test_resubmit_fails(self, node, user_role, hybrid_moderated_collection_submission):
        user = configure_test_auth(node, user_role)
        hybrid_moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.REMOVED)
        hybrid_moderated_collection_submission.save()
        with pytest.raises(PermissionsError):
            hybrid_moderated_collection_submission.resubmit(user=user, comment='Test Comment')
        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.REMOVED

    def test_hybrid_resubmit_moderator_not_submitted(self, node, hybrid_moderated_collection_submission):
        """
        Moderators can't force people to resubmit, even if it just goes back into a pending state.
        """
        configure_test_auth(node, UserRoles.MODERATOR)
        not_admin_moderator = AuthUserFactory()
        node.add_contributor(not_admin_moderator)
        hybrid_moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.REMOVED)
        hybrid_moderated_collection_submission.save()
        with pytest.raises(PermissionsError):
            hybrid_moderated_collection_submission.resubmit(user=not_admin_moderator, comment='Test Comment')
        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.REMOVED

    def test_hybrid_resubmit_moderator_submitted(self, node, hybrid_moderated_collection_submission):
        user = configure_test_auth(node, UserRoles.MODERATOR)
        node.add_contributor(user)
        hybrid_moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.REMOVED)
        hybrid_moderated_collection_submission.save()
        hybrid_moderated_collection_submission.resubmit(user=user, comment='Test Comment')
        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.ACCEPTED

    @pytest.mark.parametrize('user_role', UserRoles.excluding(UserRoles.ADMIN_USER))
    def test_cancel_fails(self, node, user_role, hybrid_moderated_collection_submission):
        user = configure_test_auth(node, user_role)
        hybrid_moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.PENDING)
        hybrid_moderated_collection_submission.save()
        with pytest.raises(PermissionsError):
            hybrid_moderated_collection_submission.cancel(user=user, comment='Test Comment')
        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.PENDING

    def test_cancel_succeeds(self, node, hybrid_moderated_collection_submission):
        user = configure_test_auth(node, UserRoles.ADMIN_USER)
        hybrid_moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.PENDING)
        hybrid_moderated_collection_submission.save()
        hybrid_moderated_collection_submission.cancel(user=user, comment='Test Comment')
        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.IN_PROGRESS
