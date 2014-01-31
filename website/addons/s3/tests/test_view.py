#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import mock
from nose.tools import *  # PEP8 asserts
#from tests.base import DbTestCase
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
        self.user_settings = self.user.get_addon('s3')
        self.node_settings = self.project.get_addon('s3')
        # Set the node addon settings to correspond to the values of the mock
        # repo
        self.node_settings = AddonS3NodeSettings()
        #self.node_settings.user = self.s3.repo.return_value['owner']['login']
        #self.node_settings.repo = self.s3.repo.return_value['name']
        self.node_settings.save()
        self.app.authenticate(*self.user.auth)

    def test_s3_page_no_user(self):
        s3 = AddonS3NodeSettings(user=None, bucket='lul')
        res = views.utils._page_content('873p', s3, None)
        assert_equals(res, {})

    def test_s3_page_no_pid(self):
        s3 = AddonS3NodeSettings(user='jimbob', bucket='lul')
        res = views.utils._page_content(None, s3, self.user_settings)
        assert_equals(res, {})

    def test_s3_page_empty_pid(self):
        s3 = AddonS3NodeSettings(user='jimbob', bucket='lul')
        res = views.utils._page_content('', s3, self.user_settings)
        assert_equals(res, {})

    def test_s3_page_no_auth(self):
        s3 = AddonS3NodeSettings(user='jimbob', bucket='lul')
        s3.node_access_key = ""
        res = views.utils._page_content('', s3, self.user_settings)
        assert_equals(res, {})

    @mock.patch('website.addons.s3.views.config.does_bucket_exist')
    @mock.patch('website.addons.s3.views.config._s3_create_access_key')
    @mock.patch('website.addons.s3.views.config.adjust_cors')
    def test_s3_settings_no_bucket(self, mock_cors, mock_create_key, mock_does_bucket_exist):
        mock_does_bucket_exist.return_value = False
        mock_create_key.return_value = True
        mock_cors.return_value = True
        url = "/api/v1/project/{0}/s3/settings/".format(self.project._id)
        res = self.app.post_json(url, {}, expect_errors=True)
        self.project.reload()
        assert_equals(self.node_settings.bucket, None)

    @mock.patch('website.addons.s3.views.utils.create_limited_user')
    def test_s3_create_access_key_attrs(self, mock_create_limited_user):
        mock_create_limited_user.return_value = {
            'access_key_id': 'Boo', 'secret_access_key': 'Riley'}
        user_settings = AddonS3UserSettings(user='Aticus-killing-mocking')
        views.utils._s3_create_access_key(
            user_settings, self.node_settings, self.project._id)
        assert_equals(self.node_settings.node_access_key, 'Boo')

    @mock.patch('website.addons.s3.views.utils.create_limited_user')
    def test_s3_create_access_key(self, mock_create_limited_user):
        mock_create_limited_user.return_value = {
            'access_key_id': 'Boo', 'secret_access_key': 'Riley'}
        user_settings = AddonS3UserSettings(user='Aticus-killing-mocking')
        assert_true(views.utils._s3_create_access_key(
            user_settings, self.node_settings, self.project._id))

    @mock.patch('framework.addons.AddonModelMixin.get_addon')
    @mock.patch('website.addons.s3.views.config.has_access')
    def test_s3_remove_user_settings(self, mock_access, mock_addon):
        mock_addon.return_value = self.user.get_addon('s3')
        mock_access.return_value = True
        self.user.get_addon('s3').access_key = 'to-kill-a-mocking-bucket'
        self.user.get_addon('s3').secret_key = 'itsasecret'
        self.user.get_addon('s3').save()
        url = '/api/v1/settings/s3/delete/'
        self.app.post_json(url, {}, auth=self.user.auth)
        # self.project.reload()
        assert_equals(self.user.get_addon('s3').access_key, '')
        # TODO finish me

    def test_download_no_file(self):
        url = "/api/v1/project/{0}/s3/fetchurl/".format(self.project._id)
        self.app.post_json(url, {},  expect_errors=True)

    # TODO fix me cant seem to be logged in.....
    @mock.patch('website.addons.s3.views.config.has_access')
    def test_user_settings_no_auth(self, mock_access):
        mock_access.return_value = False
        url = '/api/v1/settings/s3/'
        rv = self.app.post_json(url, {}, expect_errors=True)
        #assert_equals('Looks like your creditials are incorrect Could you have mistyped them?', rv['message'])

    @mock.patch('framework.addons.AddonModelMixin.get_addon')
    @mock.patch('website.addons.s3.views.config.has_access')
    def test_user_settings(self, mock_access, mock_addon):
        mock_access.return_value = True
        mock_addon.return_value = self.user.get_addon('s3')
        url = '/api/v1/settings/s3/'
        rv = self.app.post_json(
            url, {'access_key': 'scout', 'secret_key': 'Aticus'})
        user_settings = self.user.get_addon('s3')
        assert_equals(user_settings.access_key, 'scout')

    # I dont work..... Settings not getting passed around properly?
    @mock.patch('website.addons.s3.views.config.remove_user')
    def test_s3_remove_node_settings(self, mock_access):
        mock_access.return_value = True
        self.project.get_addon('s3').node_access_key = 'to-kill-a-mocking-bucket'
        self.project.get_addon('s3').node_secret_key = 'itsasecret'
        self.project.get_addon('s3').save()
        url = "/api/v1/project/{0}/s3/settings/delete/".format(self.project._id)
        self.app.post_json(url, {})
        self.project.reload()
        assert_equals(self.project.get_addon('s3').node_access_key, '')
