from api.base.settings.defaults import API_BASE

import httpretty
from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
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
