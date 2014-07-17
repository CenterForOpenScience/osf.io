# -*- coding: utf-8 -*-

import mock
from nose.tools import *

import base64
import urlparse
from StringIO import StringIO

from website.models import NodeLog

from website.addons.base.services import fileservice, hookservice

from website.addons.gitlab import settings as gitlab_settings
from website.addons.gitlab.tests import GitlabTestCase
from website.addons.gitlab.api import GitlabError
from website.addons.gitlab.services import fileservice as gitlab_fileservice
from website.addons.gitlab.services import hookservice as gitlab_hookservice


class TestServiceUtilities(GitlabTestCase):

    @mock.patch('website.addons.gitlab.services.fileservice.client.updatefile')
    @mock.patch('website.addons.gitlab.services.fileservice.client.createfile')
    def test_create_or_update_create(self, mock_create_file, mock_update_file):
        mock_create_file.return_value = None
        res = gitlab_fileservice.create_or_update(
            self.node_settings,
            self.user_settings,
            'path',
            base64.b64encode('content'),
            'master'
        )
        assert_false(mock_update_file.called)
        assert_equal(
            res,
            (NodeLog.FILE_ADDED, None)
        )

    @mock.patch('website.addons.gitlab.services.fileservice.client.updatefile')
    @mock.patch('website.addons.gitlab.services.fileservice.client.createfile')
    def test_create_or_update_update(self, mock_create_file, mock_update_file):
        mock_create_file.side_effect = GitlabError(None)
        mock_update_file.return_value = None
        res = gitlab_fileservice.create_or_update(
            self.node_settings,
            self.user_settings,
            'path',
            base64.b64encode('content'),
            'master'
        )
        assert_equal(
            res,
            (NodeLog.FILE_UPDATED, None)
        )

    @mock.patch('website.addons.gitlab.services.fileservice.client.updatefile')
    @mock.patch('website.addons.gitlab.services.fileservice.client.createfile')
    def test_create_or_update_fail(self, mock_create_file, mock_update_file):
        mock_create_file.side_effect = GitlabError(None)
        mock_update_file.side_effect = GitlabError(None)
        with assert_raises(fileservice.FileUploadError):
            gitlab_fileservice.create_or_update(
                self.node_settings,
                self.user_settings,
                'path',
                base64.b64encode('content'),
                'master'
            )


class TestFileService(GitlabTestCase):

    def setUp(self):
        super(TestFileService, self).setUp()
        self.file_service = gitlab_fileservice.GitlabFileService(
            self.node_settings
        )

    def test_upload_too_large(self):
        nchar = self.node_settings.config.max_file_size * 1024 * 1024 * 2
        sio = StringIO('q' * nchar)
        # Cowboy filename mock
        sio.filename = 'toobig.txt'
        with assert_raises(fileservice.FileTooLargeError):
            self.file_service.upload(
                'path',
                sio,
                'master',
                self.user_settings
            )

    @mock.patch('website.addons.gitlab.services.fileservice.create_or_update')
    def test_upload(self, mock_create_or_update):
        sio = StringIO('contents')
        # Cowboy filename mock
        sio.filename = 'file.txt'
        self.file_service.upload(
            'path',
            sio,
            'master',
            self.user_settings
        )
        mock_create_or_update.assert_called_once_with(
            self.node_settings,
            self.user_settings,
            'path/file.txt',
            base64.b64encode('contents'),
            branch='master',
        )

    @mock.patch('website.addons.gitlab.services.fileservice.client.getfile')
    def test_download_error(self, mock_get_file):
        mock_get_file.side_effect = GitlabError(None)
        with assert_raises(fileservice.FileDownloadError):
            self.file_service.download('file.txt', 'master')

    @mock.patch('website.addons.gitlab.services.fileservice.client.getfile')
    def test_download(self, mock_get_file):
        mock_get_file.return_value = {'content': base64.b64encode('bob')}
        res = self.file_service.download('file.txt', 'master')
        mock_get_file.assert_called_once_with(
            self.node_settings.project_id,
            'file.txt',
            'master'
        )
        assert_equal(res, 'bob')

    @mock.patch('website.addons.gitlab.services.fileservice.client.deletefile')
    def test_delete_error(self, mock_delete_file):
        mock_delete_file.side_effect = GitlabError(None)
        with assert_raises(fileservice.FileDeleteError):
            self.file_service.delete('file.txt', 'master')

    @mock.patch('website.addons.gitlab.services.fileservice.client.deletefile')
    def test_delete(self, mock_delete_file):
        self.file_service.delete('file.txt', 'master')
        mock_delete_file.assert_called_once_with(
            self.node_settings.project_id,
            'file.txt',
            'master',
            gitlab_settings.MESSAGES['delete']
        )


class TestHookService(GitlabTestCase):

    def setUp(self):
        super(TestHookService, self).setUp()
        self.hook_service = gitlab_hookservice.GitlabHookService(
            self.node_settings
        )

    def test_hook_url(self):
        assert_equal(
            gitlab_hookservice.get_hook_url(self.node_settings),
            urlparse.urljoin(
                gitlab_settings.HOOK_DOMAIN,
                self.project.api_url_for('gitlab_hook_callback')
            )
        )

    @mock.patch('website.addons.gitlab.services.hookservice.client.addprojecthook')
    def test_add_hook(self, mock_add_hook):
        mock_add_hook.return_value = {
            'id': 1,
        }
        self.hook_service.create(save=True)
        mock_add_hook.assert_called_with(
            self.node_settings.project_id,
            gitlab_hookservice.get_hook_url(self.node_settings)
        )
        assert_equal(self.node_settings.hook_id, 1)

    def test_add_hook_already_exists(self):
        self.node_settings.hook_id = 1
        with assert_raises(hookservice.HookExistsError):
            self.hook_service.create()

    @mock.patch('website.addons.gitlab.model.client.addprojecthook')
    def test_add_hook_gitlab_error(self, mock_add_hook):
        mock_add_hook.side_effect = GitlabError('Disaster')
        with assert_raises(hookservice.HookServiceError):
            self.hook_service.create()

    @mock.patch('website.addons.gitlab.model.client.deleteprojecthook')
    def test_remove_hook(self, mock_delete_hook):
        self.node_settings.hook_id = 1
        self.hook_service.delete()
        mock_delete_hook.assert_called_with(
            self.node_settings.project_id,
            1
        )
        assert_equal(
            self.node_settings.hook_id,
            None
        )

    def test_remove_hook_none_exists(self):
        with assert_raises(hookservice.HookServiceError):
            self.hook_service.delete()

    @mock.patch('website.addons.gitlab.model.client.deleteprojecthook')
    def test_remove_hook_gitlab_error(self, mock_delete_hook):
        self.node_settings.hook_id = 1
        mock_delete_hook.side_effect = GitlabError('Catastrophe')
        with assert_raises(hookservice.HookServiceError):
            self.hook_service.delete()
