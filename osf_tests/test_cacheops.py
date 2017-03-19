import pytest
from nose.tools import assert_equal

import cacheops
from cacheops.transaction import transaction_state
from django.db import transaction

from osf.models import AbstractNode, Node
from osf_tests.factories import NodeFactory


# NOTE: Special use of the `transactional_db_serializer` ensures the DB is reset on each test run.
@pytest.fixture(autouse=True)
def setup(settings, transactional_db_serializer):
    cacheops.invalidate_all()
    settings.CACHEOPS_ENABLED = False
    settings.CACHEOPS_DEGRADE_ON_FAILURE = False
    yield None
    settings.CACHEOPS_ENABLED = False


@pytest.fixture()
def title():
    return 'whoa, that\'s a thing'


@pytest.mark.django_db(transaction=True)
class TestCacheOps(object):

    def test_cacheops_is_disabled(self, settings):
        assert settings.CACHEOPS_ENABLED == False
        assert settings.CACHEOPS_DEGRADE_ON_FAILURE == False

    def test_outside_txn_typedmodels_works_with_cacheops_simple(self, settings, django_assert_num_queries, title):
        node = NodeFactory(title=title)

        settings.CACHEOPS_ENABLED = True

        with django_assert_num_queries(1):
            n = Node.objects.get(id=node.id)
            Node.objects.get(id=node.id)

        with django_assert_num_queries(1):
            AbstractNode.objects.get(id=n.id)
            AbstractNode.objects.get(id=n.id)

        new_title = 'But cacheops2'
        n.title = new_title
        n.save()

        # Verify the node cache was reset.
        with django_assert_num_queries(1):
            updated_n = Node.objects.get(id=node.id)
            assert_equal(updated_n.title, new_title)

        # Verify the base abstract node cache was reset, since we are not in a txn
        # we need to rely on cacheops to correctly reflect subclasses and invalidate.
        with django_assert_num_queries(1):
            updated_ab = AbstractNode.objects.get(id=node.id)
            assert_equal(updated_ab.title, new_title)

    def test_within_txn_typedmodels_works_with_cacheops_simple(self, settings, django_assert_num_queries, title):
        node = NodeFactory(title=title)

        settings.CACHEOPS_ENABLED = True

        with transaction.atomic():
            with django_assert_num_queries(2):
                n = Node.objects.get(id=node.id)
                ab = AbstractNode.objects.get(id=n.id)
                assert n.title == ab.title

            assert not transaction_state.is_dirty()
            new_title = 'But cacheops'
            n.title = new_title
            n.save()
            assert transaction_state.is_dirty()

            # Verify the node cache was reset.
            with django_assert_num_queries(1):
                updated_n = Node.objects.get(id=node.id)
                assert_equal(updated_n.title, new_title)

            # Verify the base abstract node cache was reset, since we are in a txn
            # we need the is_dirty flag would have been set so this should easily work.
            with django_assert_num_queries(1):
                updated_ab = AbstractNode.objects.get(id=node.id)
                assert_equal(updated_ab.title, new_title)

    def test_multiple_txn_typedmodels_works_with_cacheops_simple(self, settings, django_assert_num_queries, title):
        node = NodeFactory(title=title)
        new_title = 'But cacheops'

        settings.CACHEOPS_ENABLED = True

        # Request #1
        with transaction.atomic():
            # pre-dirty cache Node
            with django_assert_num_queries(1):
                Node.objects.get(id=node.id)
                Node.objects.get(id=node.id)

            # pre-dirty cache AbstractNode
            with django_assert_num_queries(1):
                AbstractNode.objects.get(id=node.id)
                AbstractNode.objects.get(id=node.id)

            assert not transaction_state.is_dirty()
            n = AbstractNode.objects.get(id=node.id)
            n.title = new_title
            n.save()
            assert transaction_state.is_dirty()

        # Request #2
        with transaction.atomic():
            assert not transaction_state.is_dirty()

            # Node must have been invalidated
            with django_assert_num_queries(1):
                n = Node.objects.get(id=node.id)
                assert_equal(n.title, new_title)

            # AbstractNode must have been invalidated
            with django_assert_num_queries(1):
                ab = AbstractNode.objects.get(id=node.id)
                assert_equal(ab.title, new_title)

    def test_outside_txn_typedmodels_works_with_cacheops_queryset(self, settings, django_assert_num_queries, title):
        node1 = NodeFactory(title=title)
        node2 = NodeFactory(title=title)

        settings.CACHEOPS_ENABLED = True

        n_qs = Node.objects.filter(title=title)
        ab_qs = AbstractNode.objects.filter(id__in=[node1.id, node2.id])

        with django_assert_num_queries(2):
            assert n_qs.count() == ab_qs.count()

        with django_assert_num_queries(0):
            n_qs.count()
            ab_qs.count()

        with django_assert_num_queries(2):
            n_obj = n_qs.first()
            ab_obj = ab_qs.first()
            assert ab_obj.id == n_obj.id

        with django_assert_num_queries(0):
            n_qs.first()
            ab_qs.first()

        n_obj.title = 'oh, no no'
        n_obj.save()

        # Outside a txn we rely on the typed model implementation classes to be invalidated correctly.
        with django_assert_num_queries(2):
            ab_obj = ab_qs.first()
            ab_qs.count()

        with django_assert_num_queries(0):
            ab_qs.first()
            ab_qs.count()

        assert n_obj.title == ab_obj.title

    def test_within_txn_typedmodels_works_with_cacheops_queryset(self, settings, django_assert_num_queries, title):
        node1 = NodeFactory(title=title)
        node2 = NodeFactory(title=title)

        settings.CACHEOPS_ENABLED = True

        with transaction.atomic():
            n_qs = Node.objects.filter(title=title)
            ab_qs = AbstractNode.objects.filter(id__in=[node1.id, node2.id])

            with django_assert_num_queries(2):
                assert n_qs.count() == ab_qs.count()

            with django_assert_num_queries(0):
                n_qs.count()
                ab_qs.count()

            with django_assert_num_queries(2):
                n_obj = n_qs.first()
                ab_obj = ab_qs.first()
                assert ab_obj.id == n_obj.id

            with django_assert_num_queries(0):
                n_qs.first()
                ab_qs.first()

            assert not transaction_state.is_dirty()
            n_obj.title = 'oh, no no'
            n_obj.save()
            assert transaction_state.is_dirty()

            # Since we are nested within a txn we assume any future query will bypass the cache, lets check.
            with django_assert_num_queries(2):
                ab_obj = ab_qs.first()
                ab_qs.count()

            with django_assert_num_queries(2):
                ab_qs.first()
                ab_qs.count()

            assert n_obj.title == ab_obj.title

    def test_outside_txn_queries_are_cached(self, settings, django_assert_num_queries, title):
        node = NodeFactory(title=title)

        settings.CACHEOPS_ENABLED = True

        with django_assert_num_queries(1):
            Node.objects.cache().count()
            Node.objects.cache().count()

        with django_assert_num_queries(1):
            Node.objects.get(id=node.id)
            Node.objects.get(id=node.id)

    def test_within_txn_new_item_invalidates_count_cache(self, settings, django_assert_num_queries, title):
        settings.CACHEOPS_ENABLED = True

        with transaction.atomic():
            with django_assert_num_queries(1):
                assert Node.objects.count() == 0
                Node.objects.count()

            assert not transaction_state.is_dirty()
            NodeFactory(title=title, parent=None)
            assert transaction_state.is_dirty()

            # object lookup is not cached due to insert/update/delete, txn dirty
            with django_assert_num_queries(2):
                assert Node.objects.count() == 1
                Node.objects.count()

        assert not transaction_state.is_dirty()

        # a successful commit invalidates the Node count cache
        with django_assert_num_queries(1):
            assert Node.objects.count() == 1

    def test_within_txn_populate_cache_after_commit_success(self, settings, django_assert_num_queries, title):
        settings.CACHEOPS_ENABLED = True

        with transaction.atomic():
            assert not transaction_state.is_dirty()
            node = NodeFactory(title=title)
            assert transaction_state.is_dirty()

            with django_assert_num_queries(2):
                Node.objects.get(id=node.id)
                Node.objects.get(id=node.id)

        with django_assert_num_queries(1):
            Node.objects.get(id=node.id)
            Node.objects.get(id=node.id)

    def test_within_txn_does_not_populate_cache_on_commit_failure(self, settings, django_assert_num_queries, title):
        node_id = None

        settings.CACHEOPS_ENABLED = True

        with pytest.raises(Exception, message='Error do not commit txn!'):
            with transaction.atomic():
                assert not transaction_state.is_dirty()
                node = NodeFactory(title=title)
                assert transaction_state.is_dirty()

                node_id = node.id

                with django_assert_num_queries(2):
                    assert Node.objects.filter(id=node_id).count() == 1
                    assert Node.objects.filter(id=node_id).count() == 1

                raise Exception('Error do not commit txn!')

        with django_assert_num_queries(1):
            assert Node.objects.filter(id=node_id).count() == 0
            assert Node.objects.filter(id=node_id).count() == 0

    def test_within_txn_does_not_update_cache_on_commit_failure(self, settings, django_assert_num_queries, title):
        node = NodeFactory(title=title)

        settings.CACHEOPS_ENABLED = True

        # cache the original object
        with django_assert_num_queries(1):
            Node.objects.get(id=node.id)
            Node.objects.get(id=node.id)

        with pytest.raises(Exception, message='Error do not commit txn!'):
            with transaction.atomic():
                assert not transaction_state.is_dirty()
                node.title = 'a brand new title'
                node.save()
                assert transaction_state.is_dirty()

                with django_assert_num_queries(2):
                    Node.objects.get(id=node.id)
                    Node.objects.get(id=node.id)

                raise Exception('Error do not commit txn!')

        # verify the original object remains in the cache and has not been invalidated
        with django_assert_num_queries(0):
            n1 = Node.objects.get(id=node.id)
            assert n1.title == title

    def test_within_txn_object_cache_invalidation_on_commit_success(self, settings, django_assert_num_queries, title):
        node = NodeFactory(title=title)

        settings.CACHEOPS_ENABLED = True

        # ensure cached object
        with django_assert_num_queries(1):
            Node.objects.get(id=node.id)
            Node.objects.get(id=node.id)

        with transaction.atomic():
            assert not transaction_state.is_dirty()
            node.title = 'It\'s been updated!'
            node.save()
            assert transaction_state.is_dirty()

        # verify object has been invalidated
        with django_assert_num_queries(1):
            n1 = Node.objects.get(id=node.id)
            Node.objects.get(id=node.id)
            assert n1.title == 'It\'s been updated!'

    # regression
    def test_ensure_less_naive_sql_string_matching(self, settings, django_assert_num_queries):
        # Perform a query that contains a field w/ the special word `delete`, `update` or `insert`. One of
        # these words incorrectly matched the original `is_sql_dirty` check, causing the transaction dirty
        # filter to be applied, negating further use of the cache. (https://github.com/Suor/django-cacheops/issues/234)

        settings.CACHEOPS_ENABLED = True

        with transaction.atomic():
            qs = Node.objects.filter(is_deleted=False)
            assert 'is_deleted' in str(qs.query)
            qs.count()

            # verify the query is cached
            with django_assert_num_queries(1):
                Node.objects.count()
                Node.objects.count()
