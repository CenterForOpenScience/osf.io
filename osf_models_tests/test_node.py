from modularodm import Q
from modularodm.exceptions import ValidationError as MODMValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
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

    def test_title_validation(self):
        node = NodeFactory.build(title='')
        with pytest.raises(MODMValidationError):
            node.save()
        with pytest.raises(DjangoValidationError) as excinfo:
            node.save()
        assert excinfo.value.message_dict == {'title': ['This field cannot be blank.']}

        too_long = 'a' * 201
        node = NodeFactory.build(title=too_long)
        with pytest.raises(DjangoValidationError) as excinfo:
            node.save()
        assert excinfo.value.message_dict == {'title': ['Title cannot exceed 200 characters.']}

    def test_remove_one(self):
        node = NodeFactory()
        node2 = NodeFactory()
        assert len(Node.find()) == 2  # sanity check
        Node.remove_one(node)
        assert len(Node.find()) == 1
        assert node2 in Node.find()

    def test_querying_on_guid_id(self):
        node = NodeFactory()
        assert len(node._id) == 5
        assert node in Node.find(Q('_id', 'eq', node._id))
