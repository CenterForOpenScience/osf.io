import pytest

from .factories import CommentFactory


@pytest.mark.django_db
def test_comments_have_longer_guid():
    comment = CommentFactory()
    assert len(comment._id) == 12
