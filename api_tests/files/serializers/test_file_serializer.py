from datetime import datetime

import pytest
from pytz import utc

from api.files.serializers import FileSerializer
from api_tests import utils
from osf_tests.factories import (
    UserFactory, 
    NodeFactory,
)
from tests.utils import make_drf_request_with_version

@pytest.fixture()
def user():
    return UserFactory()

@pytest.mark.django_db
class TestFileSerializer:

    @pytest.fixture()
    def node(self, user):
        return NodeFactory(creator=user)

    @pytest.fixture()
    def file_one(self, node, user):
        return utils.create_test_file(node, user)

    def test_file_serializer(self, file_one):
        date_created = file_one.versions.last().date_created
        date_modified = file_one.versions.first().date_created
        date_created_tz_aware = date_created.replace(tzinfo=utc)
        date_modified_tz_aware = date_modified.replace(tzinfo=utc)
        new_format = '%Y-%m-%dT%H:%M:%S.%fZ'

        # test_date_modified_formats_to_old_format
        req = make_drf_request_with_version(version='2.0')
        data = FileSerializer(file_one, context={'request': req}).data['data']
        assert date_modified_tz_aware == data['attributes']['date_modified']

        # test_date_modified_formats_to_new_format
        req = make_drf_request_with_version(version='2.2')
        data = FileSerializer(file_one, context={'request': req}).data['data']
        assert datetime.strftime(date_modified, new_format) == data['attributes']['date_modified']

        # test_date_created_formats_to_old_format
        req = make_drf_request_with_version(version='2.0')
        data = FileSerializer(file_one, context={'request': req}).data['data']
        assert date_created_tz_aware == data['attributes']['date_created']

        # test_date_created_formats_to_new_format
        req = make_drf_request_with_version(version='2.2')
        data = FileSerializer(file_one, context={'request': req}).data['data']
        assert datetime.strftime(date_created, new_format) == data['attributes']['date_created']
