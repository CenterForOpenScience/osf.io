# -*- coding: utf-8 -*-
from datetime import datetime
from nose.tools import *  # flake8: noqa
from pytz import utc

from osf_tests import factories
from tests.base import DbTestCase
from tests.utils import make_drf_request_with_version

from api.files.serializers import FileSerializer

from api_tests import utils


class TestFileSerializer(DbTestCase):

    def setUp(self):
        super(TestFileSerializer, self).setUp()
        self.user = factories.UserFactory()
        self.node = factories.NodeFactory(creator=self.user)
        self.file = utils.create_test_file(self.node, self.user)

        self.date_created = self.file.versions.first().date_created
        self.date_modified = self.file.versions.last().date_created
        self.date_created_tz_aware = self.date_created.replace(tzinfo=utc)
        self.date_modified_tz_aware = self.date_modified.replace(tzinfo=utc)

        self.new_format = '%Y-%m-%dT%H:%M:%S.%fZ'

    def test_date_modified_formats_to_old_format(self):
        req = make_drf_request_with_version(version='2.0')
        data = FileSerializer(self.file, context={'request': req}).data['data']
        assert_equal(self.date_modified_tz_aware, data['attributes']['date_modified'])

    def test_date_modified_formats_to_new_format(self):
        req = make_drf_request_with_version(version='2.2')
        data = FileSerializer(self.file, context={'request': req}).data['data']
        assert_equal(datetime.strftime(self.date_modified, self.new_format), data['attributes']['date_modified'])

    def test_date_created_formats_to_old_format(self):
        req = make_drf_request_with_version(version='2.0')
        data = FileSerializer(self.file, context={'request': req}).data['data']
        assert_equal(self.date_created_tz_aware, data['attributes']['date_created'])

    def test_date_created_formats_to_new_format(self):
        req = make_drf_request_with_version(version='2.2')
        data = FileSerializer(self.file, context={'request': req}).data['data']
        assert_equal(datetime.strftime(self.date_created, self.new_format), data['attributes']['date_created'])
