import pytest

from framework.auth import Auth

from website.exceptions import NodeStateError
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
    def project(self, user):
        return BookmarkCollectionFactory(creator=user)

    def test_bookmark_collection_is_bookmark_collection(self, project):
        assert project.is_bookmark_collection is True

    def test_bookmark_collection_is_collection(self, project):
        assert project.is_collection is True

    def test_cannot_remove_bookmark_collection(self, project, auth):
        with pytest.raises(NodeStateError):
            project.remove_node(auth)

    def test_cannot_have_two_bookmark_collection(self, user, project):
        with pytest.raises(NodeStateError):
            BookmarkCollectionFactory(creator=user)

    def test_cannot_link_to_bookmark_collection(self, user, auth, project):
        new_node = ProjectFactory(creator=user)
        with pytest.raises(ValueError):
            new_node.add_pointer(project, auth=auth)

    def test_can_remove_empty_folder(self, user, auth):
        new_folder = CollectionFactory(creator=user)
        assert new_folder.is_collection is True
        new_folder.remove_node(auth=auth)
        assert new_folder.is_deleted is True

    def test_can_remove_folder_structure(self, user, auth):
        outer_folder = CollectionFactory(creator=user)
        assert outer_folder.is_collection is True
        inner_folder = CollectionFactory(creator=user)
        assert inner_folder.is_collection is True
        outer_folder.add_pointer(inner_folder, auth)
        outer_folder.remove_node(auth=auth)
        assert outer_folder.is_deleted
        inner_folder.refresh_from_db()
        assert inner_folder.is_deleted
