# -*- coding: utf-8 -*-
import pytest
from datetime import datetime
from pytz import utc

from osf_tests.factories import UserFactory, NodeFactory
from tests.base import DbTestCase
from tests.utils import make_drf_request_with_version
from api.files.serializers import FileSerializer
from api_tests import utils

@pytest.fixture()
def user():
    return UserFactory()

@pytest.mark.django_db
class TestFileSerializer:

    @pytest.fixture()
    def node(self, user):
        return NodeFactory(creator=user)

    @pytest.fixture()
    def file(self, node, user):
        return utils.create_test_file(node, user)

    @pytest.fixture()
    def date_created(self, file):
        return file.versions.first().date_created

    @pytest.fixture()
    def date_modified(self, file):
        return file.versions.last().date_created

    @pytest.fixture()
    def date_created_tz_aware(self, date_created):
        return date_created.replace(tzinfo=utc)

    @pytest.fixture()
    def date_modified_tz_aware(self, date_modified):
        return  date_modified.replace(tzinfo=utc)

    @pytest.fixture()
    def new_format(self):
        return '%Y-%m-%dT%H:%M:%S.%fZ'

    def test_file_serializer(self, file, date_modified_tz_aware, date_modified, date_created, date_created_tz_aware, new_format):
        # test_date_modified_formats_to_old_format
        req = make_drf_request_with_version(version='2.0')
        data = FileSerializer(file, context={'request': req}).data['data']
        assert date_modified_tz_aware == data['attributes']['date_modified']

        # test_date_modified_formats_to_new_format
        req = make_drf_request_with_version(version='2.2')
        data = FileSerializer(file, context={'request': req}).data['data']
        assert datetime.strftime(date_modified, new_format) == data['attributes']['date_modified']

        # test_date_created_formats_to_old_format
        req = make_drf_request_with_version(version='2.0')
        data = FileSerializer(file, context={'request': req}).data['data']
        assert date_created_tz_aware == data['attributes']['date_created']

        # test_date_created_formats_to_new_format
        req = make_drf_request_with_version(version='2.2')
        data = FileSerializer(file, context={'request': req}).data['data']
        assert datetime.strftime(date_created, new_format) == data['attributes']['date_created']
