#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
from nose.tools import *  # PEP8 asserts
from tests.base import DbTestCase
from webtest_plus import TestApp

import website.app
from tests.base import DbTestCase
from tests.factories import ProjectFactory, AuthUserFactory
#from website.addons.s3.tests.utils import create_mock_s3
from website.addons.s3 import views
from website.addons.s3.model import AddonS3NodeSettings, AddonS3UserSettings

app = website.app.init_app(routes=True, set_backends=False,
                            settings_module="website.settings")

class TestS3Views(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        self.auth = ('test', self.user.api_keys[0]._primary_key)
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('s3')
        self.project.creator.add_addon('s3')

        #self.s3 = s3_mock

        self.node_settings = self.project.get_addon('s3')
        self.node_settings.user_settings = self.project.creator.get_addon('s3')
        # Set the node addon settings to correspond to the values of the mock repo
        #self.node_settings.user = self.s3.repo.return_value['owner']['login']
        #self.node_settings.repo = self.s3.repo.return_value['name']
        self.node_settings.save()

    def test_s3_page_no_user(self):
        s3 = AddonS3NodeSettings(user=None, s3_bucket='lul')
        res = views._page_content('873p', s3)
        assert_equals(res,{})

    def test_s3_page_no_pid(self):
        s3 = AddonS3NodeSettings(user='jimbob', s3_bucket='lul')
        res = views._page_content(None, s3)
        assert_equals(res,{})

    def test_s3_page_empty_pid(self):
        s3 = AddonS3NodeSettings(user='jimbob', s3_bucket='lul')
        res = views._page_content('', s3)
        assert_equals(res,{})
