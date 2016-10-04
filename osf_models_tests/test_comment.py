import pytest

from osf_models.models import Comment
from osf_models.modm_compat import Q
from .factories import CommentFactory, ProjectFactory

# All tests will require a databse
pytestmark = pytest.mark.django_db

def test_comments_have_longer_guid():
    comment = CommentFactory()
    assert len(comment._id) == 12

def test_comments_are_queryable_by_root_target():
    root_target = ProjectFactory()
    comment = CommentFactory(node=root_target)
    assert Comment.find(Q('root_target', 'eq', root_target._id))[0] == comment
