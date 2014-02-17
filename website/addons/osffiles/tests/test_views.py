#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nose.tools import *  # PEP8 asserts
from tests.base import DbTestCase
from webtest_plus import TestApp

from framework.auth.decorators import Auth
import website.app
from tests.factories import ProjectFactory, AuthUserFactory
from website.addons.osffiles.model import OsfGuidFile

app = website.app.init_app(
    routes=True, set_backends=False,
    settings_module='website.settings'
)

class TestFilesViews(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        self.auth = ('test', self.user.api_keys[0]._primary_key)
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('osffiles')
        self.node_settings = self.project.get_addon('osffiles')
        self._upload_file('firstfile', 'firstcontent')

    def _upload_file(self, name, content):
        url = self.project.api_url + 'osffiles/'
        res = self.app.post(
            url,
            upload_files=[
                ('file', name, content),
            ],
            auth=self.auth,
        )
        self.project.reload()
        return res

    def _get_hgrid_files(self):
        url = self.project.api_url + 'osffiles/hgrid/'
        return self.app.get(url, auth=self.auth).maybe_follow()

    def test_download_file(self):
        url = self.project.uploads[0].download_url(self.project)
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        assert_equal(res.body, 'firstcontent')

    def test_upload_file(self):

        post_res = self._upload_file('newfile', 'newcontent')
        get_res = self._get_hgrid_files()

        self.project.reload()
        assert_equal(
            self.project.logs[-1].action,
            'file_added'
        )

        assert_equal(post_res.status_code, 201)
        assert_true(isinstance(post_res.json, dict), 'return value is a dict')
        assert_equal(post_res.json['name'], 'newfile')

        assert_equal(len(get_res.json), 2)
        assert_equal(get_res.json[1]['name'], 'newfile')

    def test_delete_file(self):

        url = self.project.api_url + 'osffiles/firstfile/'
        post_res = self.app.delete(url, auth=self.auth).maybe_follow()
        get_res = self._get_hgrid_files()

        assert_equal(post_res.status_code, 200)
        assert_equal(len(get_res.json), 0)

    def test_file_urls(self):

        url = self.project.api_url + 'osffiles/hgrid/'
        res = self.app.get(url, auth=self.auth).maybe_follow()
        assert_equal(len(res.json), 1)
        for url in ['view', 'download', 'delete']:
            print(res.json)
            assert_in(
                self.project._id,
                res.json[0]['urls'][url]
            )

    def test_file_urls_fork(self):

        fork = self.project.fork_node(auth=Auth(user=self.user))

        url = fork.api_url + 'osffiles/hgrid/'
        res = self.app.get(url, auth=self.auth).maybe_follow()
        assert_equal(len(res.json), 1)
        for url in ['view', 'download', 'delete']:
            assert_in(
                fork._id,
                res.json[0]['urls'][url]
            )

    def test_file_urls_registration(self):

        registration = self.project.register_node(
            None, Auth(user=self.user), '', ''
        )

        url = registration.api_url + 'osffiles/hgrid/'
        res = self.app.get(url, auth=self.auth).maybe_follow()
        assert_equal(len(res.json), 1)
        for url in ['view', 'download', 'delete']:
            assert_in(
                registration._id,
                res.json[0]['urls'][url]
            )

    def test_view_creates_guid(self):

        guid_count = OsfGuidFile.find().count()

        # View file for the first time
        url = self.project.uploads[0].url(self.project)
        res = self.app.get(url, auth=self.user.auth).maybe_follow(auth=self.user.auth)

        guids = OsfGuidFile.find()

        # GUID count has been incremented by one
        assert_equal(
            guids.count(),
            guid_count + 1
        )

        # Client has been redirected to GUID
        assert_equal(
            res.request.path.strip('/'),
            guids[guids.count() - 1]._id
        )

        # View file for the second time
        self.app.get(url, auth=self.user.auth).maybe_follow()

        # GUID count has not been incremented
        assert_equal(
            OsfGuidFile.find().count(),
            guid_count + 1
        )
