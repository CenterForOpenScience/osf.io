from contextlib import suppress
from unittest import mock
import pytest
from requests import Response
from requests.exceptions import HTTPError

from osf_tests.factories import (
    AuthUserFactory,
)

from transitions import MachineError

from osf_tests.factories import NodeFactory, CollectionFactory, CollectionProviderFactory

from osf.models import CollectionSubmission, NotificationTypeEnum, CedarMetadataRecord, CedarMetadataTemplate
from osf_tests.metadata._utils import assert_equivalent_turtle
from osf.utils.workflows import CollectionSubmissionStates
from framework.exceptions import PermissionsError
from api_tests.utils import UserRoles
from api.share.utils import cedar_record_to_turtle, _shtrove_cedar_record_identifier
from django.utils import timezone
from website import settings

from tests.utils import capture_notifications


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
    with capture_notifications():
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
    with capture_notifications():
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
    with capture_notifications():
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


@pytest.fixture()
def unmoderated_collection_submission_public(node, unmoderated_collection):
    unmoderated_collection.is_public = True
    unmoderated_collection.save()
    collection_submission = CollectionSubmission(
        guid=node.guids.first(),
        collection=unmoderated_collection,
        creator=node.creator,
    )
    with capture_notifications():
        collection_submission.save()
    assert not collection_submission.is_moderated
    return collection_submission


@pytest.fixture()
def cedar_template_json():
    return {'t_key_1': 't_value_1', 't_key_2': 't_value_2', 't_key_3': 't_value_3'}


@pytest.fixture()
def cedar_template(cedar_template_json):
    return CedarMetadataTemplate.objects.create(
        schema_name='cedar_test_schema_name',
        cedar_id='cedar_test_id',
        template_version=1,
        template=cedar_template_json,
        active=True,
        should_index_for_search=True
    )


@pytest.mark.django_db
class TestModeratedCollectionSubmission:

    MOCK_NOW = timezone.now()

    def test_submit(self, moderated_collection_submission):
        # .submit on post_save
        assert moderated_collection_submission.state == CollectionSubmissionStates.PENDING

    def test_notify_contributors_pending(self, node, moderated_collection):
        with capture_notifications() as notifications:
            collection_submission = CollectionSubmission(
                guid=node.guids.first(),
                collection=moderated_collection,
                creator=node.creator,
            )
            collection_submission.save()
        assert len(notifications['emits']) == 2
        assert notifications['emits'][0]['type'] == NotificationTypeEnum.COLLECTION_SUBMISSION_SUBMITTED
        assert notifications['emits'][1]['type'] == NotificationTypeEnum.PROVIDER_NEW_PENDING_SUBMISSIONS
        assert collection_submission.state == CollectionSubmissionStates.PENDING

    def test_notify_moderators_pending(self, node, moderated_collection):

        with capture_notifications() as notifications:
            collection_submission = CollectionSubmission(
                guid=node.guids.first(),
                collection=moderated_collection,
                creator=node.creator,
            )
            collection_submission.save()
        assert len(notifications['emits']) == 2
        assert notifications['emits'][0]['type'] == NotificationTypeEnum.COLLECTION_SUBMISSION_SUBMITTED
        assert notifications['emits'][1]['type'] == NotificationTypeEnum.PROVIDER_NEW_PENDING_SUBMISSIONS
        assert collection_submission.state == CollectionSubmissionStates.PENDING

    @pytest.mark.parametrize('user_role', [UserRoles.UNAUTHENTICATED, UserRoles.NONCONTRIB])
    def test_accept_fails(self, user_role, moderated_collection_submission):
        user = configure_test_auth(node, user_role)
        with pytest.raises(PermissionsError):
            moderated_collection_submission.accept(user=user, comment='Test Comment')
        assert moderated_collection_submission.state == CollectionSubmissionStates.PENDING

    def test_accept_success(self, node, moderated_collection_submission):
        moderator = configure_test_auth(node, UserRoles.MODERATOR)
        with capture_notifications():
            moderated_collection_submission.accept(user=moderator, comment='Test Comment')
        assert moderated_collection_submission.state == CollectionSubmissionStates.ACCEPTED

    def test_notify_moderated_accepted(self, node, moderated_collection_submission):
        moderator = configure_test_auth(node, UserRoles.MODERATOR)
        with capture_notifications() as notifications:
            moderated_collection_submission.accept(user=moderator, comment='Test Comment')
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationTypeEnum.COLLECTION_SUBMISSION_ACCEPTED

        assert moderated_collection_submission.state == CollectionSubmissionStates.ACCEPTED

    @pytest.mark.parametrize('user_role', [UserRoles.UNAUTHENTICATED, UserRoles.NONCONTRIB])
    def test_reject_fails(self, node, user_role, moderated_collection_submission):
        user = configure_test_auth(node, user_role)
        with pytest.raises(PermissionsError):
            moderated_collection_submission.reject(user=user, comment='Test Comment')
        assert moderated_collection_submission.state == CollectionSubmissionStates.PENDING

    def test_reject_success(self, node, moderated_collection_submission):
        moderator = configure_test_auth(node, UserRoles.MODERATOR)
        with capture_notifications():
            moderated_collection_submission.reject(user=moderator, comment='Test Comment')
        assert moderated_collection_submission.state == CollectionSubmissionStates.REJECTED

    def test_notify_moderated_rejected(self, node, moderated_collection_submission):
        moderator = configure_test_auth(node, UserRoles.MODERATOR)

        with capture_notifications() as notifications:
            moderated_collection_submission.reject(user=moderator, comment='Test Comment')
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationTypeEnum.COLLECTION_SUBMISSION_REJECTED

        assert moderated_collection_submission.state == CollectionSubmissionStates.REJECTED

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
        with capture_notifications():
            moderated_collection_submission.remove(user=user, comment='Test Comment')
        assert moderated_collection_submission.state == CollectionSubmissionStates.REMOVED

    def test_notify_moderated_removed_moderator(self, node, moderated_collection_submission):
        moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        moderator = configure_test_auth(node, UserRoles.MODERATOR)

        with capture_notifications() as notifications:
            moderated_collection_submission.remove(user=moderator, comment='Test Comment')
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationTypeEnum.COLLECTION_SUBMISSION_REMOVED_MODERATOR

        assert moderated_collection_submission.state == CollectionSubmissionStates.REMOVED

    def test_notify_moderated_removed_admin(self, node, moderated_collection_submission):
        moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        moderator = configure_test_auth(node, UserRoles.ADMIN_USER)

        with capture_notifications() as notifications:
            moderated_collection_submission.remove(user=moderator, comment='Test Comment')
        assert len(notifications['emits']) == 2
        assert notifications['emits'][1]['type'] == NotificationTypeEnum.COLLECTION_SUBMISSION_REMOVED_ADMIN
        assert notifications['emits'][0]['type'] == NotificationTypeEnum.COLLECTION_SUBMISSION_REMOVED_ADMIN

        assert moderated_collection_submission.state == CollectionSubmissionStates.REMOVED

    def test_resubmit_success(self, node, moderated_collection_submission):
        user = configure_test_auth(node, UserRoles.ADMIN_USER)
        moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.REMOVED)
        moderated_collection_submission.save()
        with capture_notifications():
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
        with capture_notifications():
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
        with capture_notifications():
            unmoderated_collection_submission.remove(user=user, comment='Test Comment')
        assert unmoderated_collection_submission.state == CollectionSubmissionStates.REMOVED

    def test_notify_moderated_removed_admin(self, node, unmoderated_collection_submission):
        unmoderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        moderator = configure_test_auth(node, UserRoles.ADMIN_USER)

        with capture_notifications() as notifications:
            unmoderated_collection_submission.remove(user=moderator, comment='Test Comment')
        assert len(notifications['emits']) == 2
        assert notifications['emits'][0]['type'] == NotificationTypeEnum.COLLECTION_SUBMISSION_REMOVED_ADMIN
        assert notifications['emits'][1]['type'] == NotificationTypeEnum.COLLECTION_SUBMISSION_REMOVED_ADMIN
        assert unmoderated_collection_submission.state == CollectionSubmissionStates.REMOVED

    def test_resubmit_success(self, node, unmoderated_collection_submission):
        user = configure_test_auth(node, UserRoles.ADMIN_USER)
        unmoderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.REMOVED)
        unmoderated_collection_submission.save()
        with capture_notifications():
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
        with capture_notifications():
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
        with capture_notifications():
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
        with capture_notifications():
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
        with capture_notifications():
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
        with capture_notifications():
            hybrid_moderated_collection_submission.accept(user=moderator, comment='Test Comment')
        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.ACCEPTED

    def test_notify_moderated_accepted(self, node, hybrid_moderated_collection_submission):
        moderator = configure_test_auth(node, UserRoles.MODERATOR)

        with capture_notifications() as notifications:
            hybrid_moderated_collection_submission.accept(user=moderator, comment='Test Comment')
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationTypeEnum.COLLECTION_SUBMISSION_ACCEPTED
        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.ACCEPTED

    @pytest.mark.parametrize('user_role', [UserRoles.UNAUTHENTICATED, UserRoles.NONCONTRIB])
    def test_reject_fails(self, node, user_role, hybrid_moderated_collection_submission):
        user = configure_test_auth(node, user_role)
        with pytest.raises(PermissionsError):
            hybrid_moderated_collection_submission.reject(user=user, comment='Test Comment')
        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.PENDING

    def test_reject_success(self, node, hybrid_moderated_collection_submission):
        moderator = configure_test_auth(node, UserRoles.MODERATOR)
        with capture_notifications():
            hybrid_moderated_collection_submission.reject(user=moderator, comment='Test Comment')
        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.REJECTED

    def test_notify_moderated_rejected(self, node, hybrid_moderated_collection_submission):
        moderator = configure_test_auth(node, UserRoles.MODERATOR)

        with capture_notifications() as notifications:
            hybrid_moderated_collection_submission.reject(user=moderator, comment='Test Comment')
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationTypeEnum.COLLECTION_SUBMISSION_REJECTED
        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.REJECTED

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
        with capture_notifications():
            hybrid_moderated_collection_submission.remove(user=user, comment='Test Comment')
        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.REMOVED

    def test_notify_moderated_removed_moderator(self, node, hybrid_moderated_collection_submission):
        hybrid_moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        moderator = configure_test_auth(node, UserRoles.MODERATOR)

        with capture_notifications() as notifications:
            hybrid_moderated_collection_submission.remove(user=moderator, comment='Test Comment')
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationTypeEnum.COLLECTION_SUBMISSION_REMOVED_MODERATOR
        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.REMOVED

    def test_notify_moderated_removed_admin(self, node, hybrid_moderated_collection_submission):
        hybrid_moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.ACCEPTED)
        moderator = configure_test_auth(node, UserRoles.ADMIN_USER)

        with capture_notifications() as notifications:
            hybrid_moderated_collection_submission.remove(user=moderator, comment='Test Comment')
        assert len(notifications['emits']) == 2
        assert notifications['emits'][0]['type'] == NotificationTypeEnum.COLLECTION_SUBMISSION_REMOVED_ADMIN
        assert notifications['emits'][1]['type'] == NotificationTypeEnum.COLLECTION_SUBMISSION_REMOVED_ADMIN

        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.REMOVED

    def test_resubmit_success(self, node, hybrid_moderated_collection_submission):
        user = configure_test_auth(node, UserRoles.ADMIN_USER)
        hybrid_moderated_collection_submission.state_machine.set_state(CollectionSubmissionStates.REMOVED)
        hybrid_moderated_collection_submission.save()
        with capture_notifications():
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
        with capture_notifications():
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
        with capture_notifications():
            hybrid_moderated_collection_submission.cancel(user=user, comment='Test Comment')
        assert hybrid_moderated_collection_submission.state == CollectionSubmissionStates.IN_PROGRESS


@pytest.mark.django_db
@pytest.mark.enable_enqueue_task
@mock.patch.object(settings, 'SHARE_ENABLED', True)
@mock.patch.object(settings, 'USE_CELERY', False)  # run tasks synchronously
class TestCollectionSubmissionWithCedarRecord:

    @mock.patch('api.share.utils.pls_send_trove_record')
    @mock.patch('api.share.utils.share_update_cedar_metadata_record')
    @mock.patch('api.share.utils.share_delete_cedar_metadata_record')
    def test_unindexable_template_and_unpublished_record_calls_records_deletion(
        self,
        mock_delete,
        mock_create,
        mock_pls,
        unmoderated_collection_submission_public,
        cedar_template,
        cedar_template_json
    ):
        cedar_template.should_index_for_search = False
        cedar_template.save()
        record = CedarMetadataRecord.objects.create(
            guid=unmoderated_collection_submission_public.guid,
            template=cedar_template,
            metadata=cedar_template_json,
            is_published=False,
        )
        obj = mock.Mock()
        obj.status_code = 200
        mock_pls.return_value = obj
        unmoderated_collection_submission_public.save()

        assert not mock_create.s.called
        assert mock_delete.s.called
        mock_delete.s.assert_called_with(
            record.guid._id,
            record._id,
            record.template.cedar_id
        )

    @mock.patch('api.share.utils.pls_send_trove_record')
    @mock.patch('api.share.utils.share_update_cedar_metadata_record')
    @mock.patch('api.share.utils.share_delete_cedar_metadata_record')
    def test_indexable_template_and_unpublished_record_calls_records_deletion(
        self,
        mock_delete,
        mock_create,
        mock_pls,
        unmoderated_collection_submission_public,
        cedar_template,
        cedar_template_json
    ):
        cedar_template.should_index_for_search = True
        cedar_template.save()
        record = CedarMetadataRecord.objects.create(
            guid=unmoderated_collection_submission_public.guid,
            template=cedar_template,
            metadata=cedar_template_json,
            is_published=False,
        )
        obj = mock.Mock()
        obj.status_code = 200
        mock_pls.return_value = obj
        unmoderated_collection_submission_public.save()

        assert not mock_create.s.called
        assert mock_delete.s.called
        mock_delete.s.assert_called_with(
            record.guid._id,
            record._id,
            record.template.cedar_id
        )

    @mock.patch('api.share.utils.pls_send_trove_record')
    @mock.patch('api.share.utils.share_update_cedar_metadata_record')
    @mock.patch('api.share.utils.share_delete_cedar_metadata_record')
    def test_unindexable_template_and_published_record_calls_records_deletion(
        self,
        mock_delete,
        mock_create,
        mock_pls,
        unmoderated_collection_submission_public,
        cedar_template,
        cedar_template_json
    ):
        cedar_template.should_index_for_search = False
        cedar_template.save()
        record = CedarMetadataRecord.objects.create(
            guid=unmoderated_collection_submission_public.guid,
            template=cedar_template,
            metadata=cedar_template_json,
            is_published=True,
        )
        obj = mock.Mock()
        obj.status_code = 200
        mock_pls.return_value = obj
        unmoderated_collection_submission_public.save()

        assert not mock_create.s.called
        assert mock_delete.s.called
        mock_delete.s.assert_called_with(
            record.guid._id,
            record._id,
            record.template.cedar_id
        )

    @mock.patch('api.share.utils.pls_send_trove_record')
    @mock.patch('api.share.utils.share_update_cedar_metadata_record')
    @mock.patch('api.share.utils.share_delete_cedar_metadata_record')
    def test_indexable_template_and_published_record_call_shtrove(
        self,
        mock_delete,
        mock_create,
        mock_pls,
        unmoderated_collection_submission_public,
        cedar_template,
        cedar_template_json
    ):
        cedar_template.should_index_for_search = True
        cedar_template.save()
        record = CedarMetadataRecord.objects.create(
            guid=unmoderated_collection_submission_public.guid,
            template=cedar_template,
            metadata=cedar_template_json,
            is_published=True,
        )
        obj = mock.Mock()
        obj.status_code = 200
        mock_pls.return_value = obj
        unmoderated_collection_submission_public.save()

        assert mock_create.s.called
        mock_create.s.assert_called_with(unmoderated_collection_submission_public.guid._id, record.pk)
        assert not mock_delete.s.called

    def test_share_update_cedar_metadata_record(self, unmoderated_collection_submission_public, cedar_template):
        metadata = {
            '@context': {
                'pav': 'http://purl.org/pav/',
                'url': 'http://schema.org/url',
                'xsd': 'http://www.w3.org/2001/XMLSchema#',
                'name': 'http://schema.org/name',
                'oslc': 'http://open-services.net/ns/core#',
                'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
                'skos': 'http://www.w3.org/2004/02/skos/core#',
                'author': 'http://schema.org/author',
                'funder': 'https://schema.metadatacenter.org/properties/c35f0660-2072-46a3-8e0d-532e40d94919',
                'schema': 'http://schema.org/',
                'license': 'http://schema.org/license',
                'citation': 'http://schema.org/citation',
                'keywords': 'http://schema.org/keywords',
                'identifier': 'http://schema.org/identifier',
                'rdfs:label': {
                    '@type': 'xsd:string'
                },
                'description': 'http://schema.org/description',
                'schema:name': {
                    '@type': 'xsd:string'
                },
                'pav:createdBy': {
                    '@type': '@id'
                },
                'pav:createdOn': {
                    '@type': 'xsd:dateTime'
                },
                'skos:notation': {
                    '@type': 'xsd:string'
                },
                'oslc:modifiedBy': {
                    '@type': '@id'
                },
                'pav:derivedFrom': {
                    '@type': '@id'
                },
                'schema:isBasedOn': {
                    '@type': '@id'
                },
                'variableMeasured': 'http://schema.org/variableMeasured',
                'pav:lastUpdatedOn': {
                    '@type': 'xsd:dateTime'
                },
                'schema:description': {
                    '@type': 'xsd:string'
                },
                'About this template': 'https://repo.metadatacenter.org/template-fields/bc66544c-e100-439e-9e80-9b35537368e5'
            },
            'name': {
                '@value': 'name'
            },
            'description': {
                '@value': 'description'
            },
            'variableMeasured': [
                {
                    '@value': 'variable'
                }
            ],
            'author': [
                {
                    '@value': None
                }
            ],
            'citation': {
                '@value': None
            },
            'license': {
                '@value': None
            },
            'funder': [
                {
                    '@value': '1111111'
                }
            ],
            'url': {},
            'keywords': {
                '@value': None
            },
            'identifier': {}
        }
        with mock.patch('api.share.utils.pls_send_trove_record'):
            record = CedarMetadataRecord.objects.create(
                guid=unmoderated_collection_submission_public.guid,
                template=cedar_template,
                metadata=metadata,
                is_published=True,
            )

        result = cedar_record_to_turtle(record.guid.referent, record)
        expected = (
            f'@prefix ns1: <https://osf.io/vocab/2022/> .\n'
            f'@prefix ns2: <http://schema.org/> .\n'
            f'@prefix ns3: <https://schema.metadatacenter.org/properties/> .\n\n'
            f'<http://localhost:5000/{unmoderated_collection_submission_public.guid._id}> ns1:hasCedarRecord [ ns2:description "description" ;\n'
            f'            ns2:identifier [ ] ;\n'
            f'            ns2:name "name" ;\n'
            f'            ns2:url [ ] ;\n'
            f'            ns2:variableMeasured "variable" ;\n'
            f'            ns3:c35f0660-2072-46a3-8e0d-532e40d94919 "1111111" ] .\n\n'
        )
        assert_equivalent_turtle(result, expected, 'test_share_update_cedar_metadata_record')

    @mock.patch('api.share.utils.pls_send_trove_record')
    @mock.patch('api.share.utils.share_delete_cedar_metadata_record')
    def test_cedar_record_identifier_on_create(self, mock_delete, mock_pls, unmoderated_collection_submission_public):
        template = CedarMetadataTemplate.objects.create(schema_name='http://google.com', cedar_id='http26', template_version=1)
        template.should_index_for_search = True
        template.save()
        with mock.patch('api.share.utils.share_update_cedar_metadata_record'):
            to_create_record = CedarMetadataRecord.objects.create(
                guid=unmoderated_collection_submission_public.guid,
                template=template,
                metadata=template.template,
                is_published=True,
            )

        with mock.patch('api.share.utils.requests.post'):
            with mock.patch('api.share.utils._shtrove_cedar_record_identifier') as mock_identifier:
                unmoderated_collection_submission_public.save()
                mock_identifier.assert_called_with(
                    to_create_record._id,
                    to_create_record.template.cedar_id
                )
                assert (
                    _shtrove_cedar_record_identifier(to_create_record._id, to_create_record.template.cedar_id) ==
                    f'{to_create_record._id}/CedarMetadataRecord:http26'
                )

    @mock.patch('api.share.utils.pls_send_trove_record')
    @mock.patch('api.share.utils.share_update_cedar_metadata_record')
    def test_cedar_record_identifier_on_delete(self, mock_update, mock_pls, unmoderated_collection_submission_public):
        template = CedarMetadataTemplate.objects.create(schema_name='http://google.com', cedar_id='http25', template_version=1)
        with mock.patch('api.share.utils.share_delete_cedar_metadata_record'):
            to_delete_record = CedarMetadataRecord.objects.create(
                guid=unmoderated_collection_submission_public.guid,
                template=template,
                metadata=template.template,
                is_published=False,
            )

        with mock.patch('api.share.utils.requests.delete'):
            with mock.patch('api.share.utils._shtrove_cedar_record_identifier') as mock_identifier:
                unmoderated_collection_submission_public.save()
                mock_identifier.assert_called_with(to_delete_record._id, to_delete_record.template.cedar_id)
                assert (
                    _shtrove_cedar_record_identifier(to_delete_record._id, to_delete_record.template.cedar_id) ==
                    f'{to_delete_record._id}/CedarMetadataRecord:http25'
                )

    @mock.patch('api.share.utils.share_update_cedar_metadata_record')
    @mock.patch('api.share.utils.share_delete_cedar_metadata_record')
    def test_cedar_record_create_retry(
        self,
        mock_delete,
        mock_create,
        unmoderated_collection_submission_public,
        cedar_template,
        cedar_template_json
    ):
        cedar_template.should_index_for_search = True
        cedar_template.save()
        with mock.patch('api.share.utils.pls_send_trove_record') as mock_pls:
            mock_pls.return_value = Response()
            mock_pls.return_value.status_code = 400
            with suppress(Exception):
                CedarMetadataRecord.objects.create(
                    guid=unmoderated_collection_submission_public.guid,
                    template=cedar_template,
                    metadata=cedar_template_json,
                    is_published=True,
                )

            def mock_raise_for_status(*args, **kwargs):
                raise HTTPError('Retry error')

            mock_pls.return_value = Response()
            mock_pls.return_value.status_code = 400
            mock_pls.return_value.raise_for_status = mock_raise_for_status
            try:
                unmoderated_collection_submission_public.save()
            except Exception as err:
                assert str(err) == "Retry in 180s: HTTPError('Retry error')"
                assert not mock_create.s.called
                assert not mock_delete.s.called
            else:
                pytest.fail('Expected Retry(HTTPError) to be raised')

    @mock.patch('api.share.utils.share_update_cedar_metadata_record')
    @mock.patch('api.share.utils.share_delete_cedar_metadata_record')
    def test_cedar_record_delete_retry(
        self,
        mock_delete,
        mock_create,
        unmoderated_collection_submission_public,
        cedar_template,
        cedar_template_json
    ):
        cedar_template.should_index_for_search = False
        cedar_template.save()
        with mock.patch('api.share.utils.pls_send_trove_record') as mock_pls:
            mock_pls.return_value = Response()
            mock_pls.return_value.status_code = 400
            with suppress(Exception):
                CedarMetadataRecord.objects.create(
                    guid=unmoderated_collection_submission_public.guid,
                    template=cedar_template,
                    metadata=cedar_template_json,
                    is_published=True,
                )

            def mock_raise_for_status(*args, **kwargs):
                raise HTTPError('Retry error')

            mock_pls.return_value = Response()
            mock_pls.return_value.status_code = 400
            mock_pls.return_value.raise_for_status = mock_raise_for_status
            try:
                unmoderated_collection_submission_public.save()
            except Exception as err:
                assert str(err) == "Retry in 180s: HTTPError('Retry error')"
                assert not mock_create.s.called
                assert not mock_delete.s.called
            else:
                pytest.fail('Expected Retry(HTTPError) to be raised')
