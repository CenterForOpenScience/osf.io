from modularodm import Q
import pytest

from osf_models.models import Node
from .factories import NodeFactory

@pytest.mark.django_db
class TestNodeMODMCompat:

    def test_basic_querying(self):
        node_1 = NodeFactory(is_public=False)
        node_2 = NodeFactory(is_public=True)

        results = Node.find()
        assert len(results) == 2

        private = Node.find(Q('is_public', 'eq', False))
        assert node_1 in private
        assert node_2 not in private

    def test_compound_query(self):
        node = NodeFactory(is_public=True, title='foo')

        assert node in Node.find(Q('is_public', 'eq', True) & Q('title', 'eq', 'foo'))
        assert node not in Node.find(Q('is_public', 'eq', False) & Q('title', 'eq', 'foo'))
