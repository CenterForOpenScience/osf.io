from modularodm import Q
import pytest

from osf.models import ArchiveTarget

@pytest.mark.django_db
def test_querying_on_id():
    # Test that queries on _id on models that inherit from ObjectIDMixin are
    # translated properly
    archive_target = ArchiveTarget(name='s3', stat_result={}, errors=[])
    archive_target.save()
    assert archive_target in ArchiveTarget.find(Q('_id', 'eq', archive_target._id))
