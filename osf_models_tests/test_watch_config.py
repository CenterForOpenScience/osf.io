import pytest

from osf_models.models import WatchConfig
from .factories import UserFactory, NodeFactory, ProjectFactory

pytestmark = pytest.mark.django_db

@pytest.fixture()
def user():
    return UserFactory()

def test_watched_watchers_relationship(user):
    project = ProjectFactory()
    WatchConfig.objects.create(user=user, node=project)
    assert user in project.watches.all()
    assert project in user.watched.all()

# copied from tests/test_models.py#TestUser
def test_User_is_watching(user):
    # User watches a node
    watched_node = NodeFactory()
    WatchConfig.objects.create(user=user, node=watched_node)
    unwatched_node = NodeFactory()
    assert user.is_watching(watched_node) is True
    assert user.is_watching(unwatched_node) is False
