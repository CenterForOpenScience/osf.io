"""Tests for osf.utils.manager.IncludeQueryset"""
import pytest

from framework.auth import Auth
from osf.models import Node
from osf_tests.factories import ProjectFactory, NodeFactory, UserFactory


pytestmark = pytest.mark.django_db


@pytest.fixture()
def create_n_nodes():
    def _create_n_nodes(n, roots=True):
        return [
            ProjectFactory() if roots else NodeFactory()
            for _ in range(n)
        ]
    return _create_n_nodes

class TestIncludeQuerySet:

    @pytest.mark.django_assert_num_queries
    def test_include_guids(self, create_n_nodes, django_assert_num_queries):
        create_n_nodes(3)
        # Confirm guids included automagically
        with django_assert_num_queries(1):
            for node in Node.objects.all():
                assert node._id is not None
        with django_assert_num_queries(1):
            for node in Node.objects.include('guids').all():
                assert node._id is not None

    @pytest.mark.django_assert_num_queries
    def test_include_guids_filter(self, create_n_nodes, django_assert_num_queries):
        nodes = create_n_nodes(3)
        nids = [e.id for e in nodes[:-1]]

        with django_assert_num_queries(1):
            for node in Node.objects.include('guids').filter(id__in=nids):
                assert node._id is not None

    @pytest.mark.django_assert_num_queries
    def test_include_root_guids(self, create_n_nodes, django_assert_num_queries):
        nodes = create_n_nodes(3, roots=False)

        queryset = Node.objects.filter(id__in=[e.id for e in nodes]).include('root__guids')
        with django_assert_num_queries(1):
            for node in queryset:
                assert node.root._id is not None

    @pytest.mark.django_assert_num_queries
    def test_include_contributor_user_guids(self, create_n_nodes, django_assert_num_queries):
        nodes = create_n_nodes(3)
        for node in nodes:
            for _ in range(3):
                contrib = UserFactory()
                node.add_contributor(contrib, auth=Auth(node.creator), save=True)

        nodes = Node.objects.include('contributor__user__guids').all()
        for node in nodes:
            with django_assert_num_queries(0):
                for contributor in node.contributor_set.all():
                    assert contributor.user._id is not None
