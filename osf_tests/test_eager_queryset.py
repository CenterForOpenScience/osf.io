import pytest

from osf.models import Node
from osf_tests.factories import NodeFactory


@pytest.mark.django_db
class TestEagerQuerySet:
    @pytest.mark.django_assert_num_queries
    def test_select_related_does_correct_query(self, django_assert_num_queries):
        node = NodeFactory()
        node_id = node.id
        with django_assert_num_queries(1):
            fresh_node = Node.objects.select_related('creator').get(id=node_id)
            cr = fresh_node.creator

    @pytest.mark.django_assert_num_queries
    def test_eager_fk_does_correct_query(self, django_assert_num_queries):
        node = NodeFactory()
        node_id = node.id
        with django_assert_num_queries(1):
            fresh_node = Node.objects.eager('creator').get(id=node_id)
            cr = fresh_node.creator

    @pytest.mark.django_assert_num_queries
    def test_lazy_fk_does_correct_queries(self, django_assert_num_queries):
        node = NodeFactory()
        node_id = node.id
        with django_assert_num_queries(2):
            fresh_node = Node.objects.get(id=node_id)
            cr = fresh_node.creator
