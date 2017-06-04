from modularodm import Q
from nose.tools import *  # flake8: noqa

from api.search.serializers import SearchSerializer
from api_tests import utils

from tests.base import DbTestCase
from tests.factories import (
    AuthUserFactory,
    NodeFactory,
    ProjectFactory,
)
from tests.utils import make_drf_request_with_version, mock_archive

from website.models import MetaSchema
from website.project.model import ensure_schemas
from website.project.metadata.schemas import LATEST_SCHEMA_VERSION
from website.search import search


class TestSearchSerializer(DbTestCase):

    def setUp(self):
        super(TestSearchSerializer, self).setUp()

        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user, is_public=True)
        self.component = NodeFactory(parent=self.project, creator=self.user, is_public=True)
        self.file = utils.create_test_file(self.component, self.user)

        ensure_schemas()
        self.schema = MetaSchema.find_one(
            Q('name', 'eq', 'Replication Recipe (Brandt et al., 2013): Post-Completion') &
            Q('schema_version', 'eq', LATEST_SCHEMA_VERSION)
        )

        with mock_archive(self.project, autocomplete=True, autoapprove=True, schema=self.schema) as registration:
            self.registration = registration

    def tearDown(self):
        super(TestSearchSerializer, self).tearDown()
        search.delete_all()

    def test_search_serializer_mixed_model_project(self):
        req = make_drf_request_with_version(version='2.0')
        result = SearchSerializer(self.project, context={'request': req}).data
        assert_equal(result['data']['type'], 'nodes')

    def test_search_serializer_mixed_model_component(self):
        req = make_drf_request_with_version(version='2.0')
        result = SearchSerializer(self.component, context={'request': req}).data
        assert_equal(result['data']['type'], 'nodes')

    def test_search_serializer_mixed_model_registration(self):
        req = make_drf_request_with_version(version='2.0')
        result = SearchSerializer(self.registration, context={'request': req}).data
        assert_equal(result['data']['type'], 'registrations')

    def test_search_serializer_mixed_model_file(self):
        req = make_drf_request_with_version(version='2.0')
        result = SearchSerializer(self.file, context={'request': req}).data
        assert_equal(result['data']['type'], 'files')

    def test_search_serializer_mixed_model_user(self):
        req = make_drf_request_with_version(version='2.0')
        result = SearchSerializer(self.user, context={'request': req}).data
        assert_equal(result['data']['type'], 'users')
