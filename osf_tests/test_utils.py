import pytest

from osf.models import Node
from osf.utils.migrations import disable_auto_now_fields
from osf_tests.factories import NodeFactory

pytestmark = pytest.mark.django_db

@pytest.fixture()
def node():
    return NodeFactory()


class TestDisableAutoNowContextManager:

    def test_auto_now_not_updated(self, node):
        # update, save, confirm date changes
        original_date_modified = node.date_modified
        node.title = 'A'
        node.save()
        assert node.date_modified != original_date_modified

        # update and save within context manager, confirm date doesn't change (i.e. auto_now was set to False)
        new_date_modified = node.date_modified
        with disable_auto_now_fields(Node):
            node.title = 'AB'
            node.save()
        assert node.date_modified == new_date_modified

        # update, save, confirm date changes (i.e. that auto_now was set back to True)
        node.title = 'ABC'
        node.save()
        assert node.date_modified != new_date_modified
