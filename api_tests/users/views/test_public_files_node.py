from api.base.settings.defaults import API_BASE

import httpretty
import pytz
from nose.tools import *  # flake8: noqa

from api_tests.files.views.test_file_detail import _dt_to_iso8601
from api_tests import utils as api_utils

from tests.base import ApiTestCase
from tests.factories import (
    AuthUserFactory,
    PublicFilesFactory
)

class TestNodePublicFiles(ApiTestCase):

    def setUp(self):
        super(TestNodePublicFiles, self).setUp()
        self.user = AuthUserFactory()
        self.public_files_node = PublicFilesFactory(creator=self.user)
        self.url = '/{}users/{}/public_files/'.format(API_BASE, self.user._id)
        self.public_files_node.get_addon('osfstorage').get_root().append_file('NewFile')
        self.file = api_utils.create_test_file(self.public_files_node, self.user, create_guid=False)
        self.file_url = '/{}files/{}/'.format(API_BASE, self.file._id)

        httpretty.enable()

    def tearDown(self):
        super(TestNodePublicFiles, self).tearDown()
        httpretty.disable()
        httpretty.reset()

    def test_returns_public_files_logged_out(self):
        res = self.app.get(self.url, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['attributes']['provider'], 'osfstorage')
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_get_file(self):
        res = self.app.get(self.file_url, auth=self.user.auth)
        self.file.versions[-1]._clear_caches()
        self.file.versions[-1].reload()
        assert_equal(res.status_code, 200)
        assert_equal(res.json.keys(), ['data'])
        attributes = res.json['data']['attributes']
        assert_equal(attributes['path'], self.file.path)
        assert_equal(attributes['kind'], self.file.kind)
        assert_equal(attributes['name'], self.file.name)
        assert_equal(attributes['materialized_path'], self.file.materialized_path)
        assert_equal(attributes['last_touched'], None)
        assert_equal(attributes['provider'], self.file.provider)
        assert_equal(attributes['size'], self.file.versions[-1].size)
        assert_equal(attributes['date_modified'], _dt_to_iso8601(self.file.versions[-1].date_created.replace(tzinfo=pytz.utc)))
        assert_equal(attributes['date_created'], _dt_to_iso8601(self.file.versions[0].date_created.replace(tzinfo=pytz.utc)))
        assert_equal(attributes['extra']['hashes']['md5'], None)
        assert_equal(attributes['extra']['hashes']['sha256'], None)
        assert_equal(attributes['tags'], [])
