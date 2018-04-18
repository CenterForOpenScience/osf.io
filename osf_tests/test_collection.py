import pytest

from django.db import IntegrityError

from framework.auth import Auth

from osf.models import Collection
from website.exceptions import NodeStateError
from website.views import find_bookmark_collection
from .factories import (
    UserFactory,
    ProjectFactory,
    BookmarkCollectionFactory,
    CollectionFactory,
)

pytestmark = pytest.mark.django_db

@pytest.fixture()
def user():
    return UserFactory()

@pytest.fixture()
def auth(user):
    return Auth(user)

# copied from tests/test_models.py
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
