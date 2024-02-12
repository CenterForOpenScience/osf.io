from unittest import mock
import pytest

from django.db import IntegrityError

from framework.auth import Auth

from osf.models import Collection
from osf.exceptions import NodeStateError
from website.views import find_bookmark_collection
from .factories import (
    UserFactory,
    ProjectFactory,
    BookmarkCollectionFactory,
    CollectionFactory,
    CollectionProviderFactory
)
from osf.utils.workflows import CollectionSubmissionStates
from website.mails import mails
from osf.models.collection_submission import mails as collection_submission_mail

pytestmark = pytest.mark.django_db

@pytest.fixture()
def user():
    return UserFactory()

@pytest.fixture()
def auth(user):
    return Auth(user)

# copied from tests/test_models.py
@pytest.mark.enable_bookmark_creation
class TestBookmarkCollection:

    @pytest.fixture()
    def collection(self, user):
        return find_bookmark_collection(user)

    def test_bookmark_collection_is_bookmark_collection(self, collection):
        assert collection.is_bookmark_collection
        assert isinstance(collection, Collection)

    def test_cannot_remove_bookmark_collection(self, collection):
        with pytest.raises(NodeStateError):
            collection.delete()

    def test_cannot_have_two_bookmark_collection(self, user, collection):
        with pytest.raises(IntegrityError):
            BookmarkCollectionFactory(creator=user)

    def test_cannot_link_to_bookmark_collection(self, user, auth, collection):
        new_node = ProjectFactory(creator=user)
        with pytest.raises(ValueError):
            new_node.add_pointer(collection, auth=auth)

    def test_can_remove_empty_folder(self, user, auth):
        new_folder = CollectionFactory(creator=user)
        assert isinstance(new_folder, Collection)
        new_folder.delete()
        assert new_folder.deleted

    def test_can_remove_root_folder_structure_without_cascading(self, user, auth):
        outer_folder = CollectionFactory(creator=user)
        assert isinstance(outer_folder, Collection)
        inner_folder = CollectionFactory(creator=user)
        assert isinstance(inner_folder, Collection)
        outer_folder.collect_object(inner_folder, auth.user)
        outer_folder.delete()
        assert outer_folder.deleted
        inner_folder.refresh_from_db()
        assert not inner_folder.deleted


@pytest.mark.enable_bookmark_creation
class TestImplicitRemoval:

    @pytest.fixture
    def bookmark_collection(self, user):
        return find_bookmark_collection(user)

    @pytest.fixture
    def user2(self):
        return UserFactory()

    @pytest.fixture
    def alternate_bookmark_collection(self, user2):
        return find_bookmark_collection(user2)

    @pytest.fixture
    def standard_collection(self):
        return CollectionFactory()

    @pytest.fixture
    def collected_node(self, bookmark_collection, alternate_bookmark_collection, standard_collection):
        node = ProjectFactory(creator=bookmark_collection.creator, is_public=True)
        bookmark_collection.collect_object(node, bookmark_collection.creator)
        alternate_bookmark_collection.collect_object(node, alternate_bookmark_collection.creator)
        standard_collection.collect_object(node, standard_collection.creator)
        return node

    @pytest.fixture
    def provider(self):
        return CollectionProviderFactory()

    @pytest.fixture
    def provider_collection(self, provider):
        return CollectionFactory(provider=provider)

    @pytest.fixture
    def provider_collected_node(self, bookmark_collection, alternate_bookmark_collection, provider_collection):
        node = ProjectFactory(creator=bookmark_collection.creator, is_public=True)
        bookmark_collection.collect_object(node, bookmark_collection.creator)
        alternate_bookmark_collection.collect_object(node, alternate_bookmark_collection.creator)
        provider_collection.collect_object(node, provider_collection.creator)
        return node

    @mock.patch('osf.models.node.Node.check_privacy_change_viability', mock.Mock())  # mocks the storage usage limits
    def test_node_removed_from_collection_on_privacy_change(self, auth, collected_node, bookmark_collection):
        associated_collections = collected_node.guids.first().collectionsubmission_set
        assert associated_collections.count() == 3

        collected_node.set_privacy('private', auth=auth)

        assert associated_collections.filter(machine_state=CollectionSubmissionStates.REMOVED).count() == 2
        assert associated_collections.exclude(machine_state=CollectionSubmissionStates.REMOVED).count() == 1
        assert associated_collections.filter(collection=bookmark_collection).exists()

    @mock.patch('osf.models.node.Node.check_privacy_change_viability', mock.Mock())  # mocks the storage usage limits
    def test_node_removed_from_collection_on_privacy_change_notify(self, auth, provider_collected_node, bookmark_collection):
        associated_collections = provider_collected_node.guids.first().collectionsubmission_set
        assert associated_collections.count() == 3

        send_mail = mails.send_mail
        with mock.patch.object(collection_submission_mail, 'send_mail') as mock_send:
            mock_send.side_effect = send_mail  # implicitly test rendering
            provider_collected_node.set_privacy('private', auth=auth)
            assert mock_send.called
            assert len(mock_send.call_args_list) == 1
            email1 = mock_send.call_args_list[0]
            _, email1_kwargs = email1
            assert {email1_kwargs['node'].id} == {provider_collected_node.id}
            expected_mail = mails.COLLECTION_SUBMISSION_REMOVED_PRIVATE(associated_collections.last().collection, provider_collected_node)
            assert {email1_kwargs['mail'].tpl_prefix} == {expected_mail.tpl_prefix}

    @mock.patch('osf.models.node.Node.check_privacy_change_viability', mock.Mock())  # mocks the storage usage limits
    def test_node_removed_from_collection_on_privacy_change_no_provider(self, auth, collected_node, bookmark_collection):
        associated_collections = collected_node.guids.first().collectionsubmission_set
        assert associated_collections.count() == 3

        send_mail = mails.send_mail
        with mock.patch.object(collection_submission_mail, 'send_mail') as mock_send:
            mock_send.side_effect = send_mail  # implicitly test rendering
            collected_node.set_privacy('private', auth=auth)
            assert not mock_send.called

    def test_node_removed_from_collection_on_delete(self, collected_node, bookmark_collection, auth):
        associated_collections = collected_node.guids.first().collectionsubmission_set
        assert associated_collections.filter(machine_state=CollectionSubmissionStates.ACCEPTED).count() == 3

        collected_node.remove_node(auth)

        assert associated_collections.filter(machine_state=CollectionSubmissionStates.REMOVED).count() == 3
