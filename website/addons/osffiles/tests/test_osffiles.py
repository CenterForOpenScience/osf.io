#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nose.tools import *  # noqa (PEP8 asserts)
from tests.base import OsfTestCase
from StringIO import StringIO

from framework.auth import Auth
from tests.factories import ProjectFactory, AuthUserFactory, PrivateLinkFactory
from website import settings
from website.project.views.file import prepare_file

from website.addons.osffiles.model import OsfGuidFile
from website.addons.osffiles.utils import get_current_file_version
from website.addons.osffiles.exceptions import FileNotFoundError

class TestFilesViews(OsfTestCase):

    def setUp(self):

        super(TestFilesViews, self).setUp()

        self.user = AuthUserFactory()
        self.auth = ('test', self.user.api_keys[0]._primary_key)
        self.consolidated_auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('osffiles', auth=self.consolidated_auth)
        self.node_settings = self.project.get_addon('osffiles')
        self.fid = 'firstfile'
        self._upload_file(self.fid, 'firstcontent')

    def _upload_file(self, name, content, **kwargs):
        url = self.project.api_url + 'osffiles/'
        res = self.app.post(
            url,
            upload_files=[
                ('file', name, content),
            ],
            auth=self.auth,
            **kwargs
        )
        self.project.reload()
        return res

    def test_download_file(self):
        url = self.project.uploads[0].download_url(self.project)
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        assert_equal(res.body, 'firstcontent')

    def test_download_file_by_version_with_bad_version_value(self):
        # FIXME: self.project.api_url_for doesn't seem to be working here. lolz
        url = '/project/{}/osffiles/{}/version/bad/download/'.format(
            self.project._id, self.fid
        )

        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_in('Invalid version', res.json['message_short'])

    def test_download_file_by_version_with_bad_version_number(self):
        url = '/project/{}/osffiles/{}/version/9999/download/'.format(
            self.project._id, self.fid
        )

        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_download_file_by_version_with_negative_version_number(self):

        url = '/project/{}/osffiles/{}/version/-1/download/'.format(
            self.project._id, self.fid
        )

        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_upload_file(self):

        node_addon = self.project.get_addon('osffiles')

        res = self._upload_file(
            'newfile',
            'a' * (node_addon.config.max_file_size),
            expect_errors=True,
        )

        self.project.reload()
        assert_equal(
            self.project.logs[-1].action,
            'file_added'
        )

        assert_equal(res.status_code, 201)
        assert_true(isinstance(res.json, dict), 'return value is a dict')
        assert_equal(res.json['name'], 'newfile')

        assert_in('newfile', self.project.files_current)

    def test_upload_file_too_large(self):

        node_addon = self.project.get_addon('osffiles')

        res = self._upload_file(
            'newfile',
            'a' * (node_addon.config.max_file_size + 1),
            expect_errors=True,
        )

        self.project.reload()

        assert_equal(res.status_code, 400)
        assert_not_in('newfile', self.project.files_current)

    def test_view_file_with_anonymous_link(self):
        link = PrivateLinkFactory(anonymous=True)
        link.nodes.append(self.project)
        link.save()
        self._upload_file('firstfile', 'secondcontent')
        url = self.project.api_url_for(
            'file_info', fid=self.project.uploads[0].filename
        )
        res = self.app.get(url, {'view_only': link.key})
        assert_not_in(self.user.fullname, res.body)
        assert_not_in(self.user._id, res.body)

    def test_delete_file(self):

        url = self.project.api_url + 'osffiles/firstfile/'
        res = self.app.delete(url, auth=self.auth).maybe_follow()
        assert_equal(res.status_code, 200)
        self.project.reload()
        assert_not_in('firstfile', self.project.files_current)

    def test_file_urls(self):

        url = self.project.api_url + 'osffiles/hgrid/'
        res = self.app.get(url, auth=self.auth).maybe_follow()
        assert_equal(len(res.json), 1)
        for url in ['view', 'download', 'delete']:
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

def make_file_like(name='file', content='data'):
    sio = StringIO(content)
    sio.filename = name
    sio.content_type = 'text/html'
    return sio

class TestUtils(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.project = ProjectFactory()

    def test_prepare_file_name(self):
        name, content, content_type, size = prepare_file(make_file_like(
            name='file')
        )
        assert_equal(name, 'file')

    def test_prepare_file_name_missing(self):
        name, content, content_type, size = prepare_file(
            make_file_like(name='ü')
        )
        assert_equal(name, settings.MISSING_FILE_NAME)

    def test_get_current_file_version(self):
        self.project.add_file(Auth(self.project.creator), 'foo', 'somecontent', 128, 'rst')
        result = get_current_file_version('foo', node=self.project)
        assert_equal(result, 0)
        # Update the file
        self.project.add_file(Auth(self.project.creator), 'foo', 'newcontent', 128, 'rst')
        result = get_current_file_version('foo', node=self.project)
        assert_equal(result, 1)

    def test_get_current_file_raises_error_when_file_not_found(self):
        with assert_raises(FileNotFoundError):
            get_current_file_version('notfound', node=self.project)
