import mock
from nose.tools import *
from webtest import Upload

import datetime
import httplib as http

from tests.base import fake

from website.models import NodeLog
from website.addons.base.services import fileservice

from website.addons.gitlab import settings as gitlab_settings
from website.addons.gitlab.views import hooks
from website.addons.gitlab import utils

from website.addons.gitlab.tests import GitlabTestCase
from website.addons.gitlab.tests.factories import GitlabGuidFileFactory
from website.addons.gitlab.views.hooks import add_diff_log


add_file_data = {u'a_mode': None,
  u'b_mode': u'100644',
  u'deleted_file': False,
  u'diff': u'--- /dev/null\n+++ b/blah.py\n@@ -1 +1,2 @@\n+import this',
  u'new_file': True,
  u'new_path': u'blah.py',
  u'old_path': u'blah.py',
  u'renamed_file': False}

update_file_data = {u'a_mode': None,
  u'b_mode': u'100644',
  u'deleted_file': False,
  u'diff': u'--- a/blah.py\n+++ b/blah.py\n@@ -1,2 +1,3 @@\n import this\n+import that',
  u'new_file': False,
  u'new_path': u'blah.py',
  u'old_path': u'blah.py',
  u'renamed_file': False}

delete_file_data = {u'a_mode': None,
  u'b_mode': None,
  u'deleted_file': True,
  u'diff': u'--- a/blah.py\n+++ /dev/null\n@@ -1,3 +1 @@\n-import this\n-import that',
  u'new_file': False,
  u'new_path': u'blah.py',
  u'old_path': u'blah.py',
  u'renamed_file': False}


class TestHookLog(GitlabTestCase):

    def _handle_diff(self, data, user):
        add_diff_log(
            self.project,
            data,
            sha='e5a7e862ba74fbd765ba6f48c33714adf621b73b',
            date=datetime.datetime.now(),
            gitlab_user=user,
            save=True,
        )

    def test_hook_add_file_osf_user(self):
        log_count = len(self.project.logs)
        self._handle_diff(add_file_data, self.user)
        assert_equal(len(self.project.logs), log_count + 1)
        assert_equal(self.project.logs[-1].params['path'], add_file_data['new_path'])
        assert_equal(self.project.logs[-1].user, self.user)
        assert_equal(self.project.logs[-1].foreign_user, None)
        assert_equal(
            self.project.logs[-1].action,
            'gitlab_{0}'.format(NodeLog.FILE_ADDED)
        )

    def test_hook_add_file_foreign_user(self):
        log_count = len(self.project.logs)
        self._handle_diff(add_file_data, 'Freddie')
        assert_equal(len(self.project.logs), log_count + 1)
        assert_equal(self.project.logs[-1].params['path'], add_file_data['new_path'])
        assert_equal(self.project.logs[-1].user, None)
        assert_equal(self.project.logs[-1].foreign_user, 'Freddie')
        assert_equal(
            self.project.logs[-1].action,
            'gitlab_{0}'.format(NodeLog.FILE_ADDED)
        )

    def test_hook_update_file(self):
        log_count = len(self.project.logs)
        self._handle_diff(update_file_data, 'Freddie')
        assert_equal(len(self.project.logs), log_count + 1)
        assert_equal(self.project.logs[-1].params['path'], update_file_data['new_path'])
        assert_equal(self.project.logs[-1].foreign_user, 'Freddie')
        assert_equal(
            self.project.logs[-1].action,
            'gitlab_{0}'.format(NodeLog.FILE_UPDATED)
        )

    def test_hook_delete_file(self):
        log_count = len(self.project.logs)
        self._handle_diff(delete_file_data, 'Freddie')
        assert_equal(len(self.project.logs), log_count + 1)
        assert_equal(self.project.logs[-1].params['path'], delete_file_data['new_path'])
        assert_equal(self.project.logs[-1].foreign_user, 'Freddie')
        assert_equal(
            self.project.logs[-1].action,
            'gitlab_{0}'.format(NodeLog.FILE_REMOVED)
        )

    @mock.patch('website.addons.gitlab.views.hooks.add_diff_log')
    @mock.patch('website.addons.gitlab.views.hooks.client.listrepositorycommitdiff')
    def test_add_log_from_osf(self, mock_list_diff, mock_add_log):
        payload = {
            'id': '47b79b37ef1cf6f944f71ea13c6667ddd98b9804',
            'message': gitlab_settings.MESSAGES['add'],
            'timestamp': '2014-03-31T13:40:39+00:00',
            'author': {
                'name': self.user.fullname,
                'email': self.user.username,
            }
        }
        hooks.add_hook_log(self.node_settings, payload, save=True)
        assert_false(mock_list_diff.called)
        assert_false(mock_add_log.called)

    @mock.patch('website.addons.gitlab.views.hooks.add_diff_log')
    @mock.patch('website.addons.gitlab.views.hooks.client.listrepositorycommitdiff')
    def test_add_log_from_non_osf_user(self, mock_list_diff, mock_add_log):
        name, email = fake.name(), fake.email()
        payload = {
            'id': '47b79b37ef1cf6f944f71ea13c6667ddd98b9804',
            'message': 'pushed from git',
            'timestamp': '2014-03-31T13:40:39+00:00',
            'author': {
                'name': name,
                'email': email,
            }
        }
        mock_list_diff.return_value = [{'fake': 'diff'}]
        hooks.add_hook_log(self.node_settings, payload, save=True)
        assert_true(mock_list_diff.called)
        assert_true(mock_add_log.called)


class TestListFiles(GitlabTestCase):

    @mock.patch('website.addons.gitlab.views.crud.client.listrepositorytree')
    def test_list_files_no_id(self, mock_list):
        self.node_settings.project_id = None
        self.node_settings.save()
        res = self.app.get(
            self.project.api_url_for('gitlab_list_files'),
            auth=self.user.auth
        )
        assert_equal(res.json, [])
        assert_false(mock_list.called)

    @mock.patch('website.addons.gitlab.views.crud.client.listrepositorytree')
    def test_list_files(self, mock_list):
        mock_list.return_value = [
            {
                'id': '56b21c430947a764518960dad08f913e2f86eb43',
                'mode': '100644',
                'name': 'science.txt',
                'type': 'blob',
            }
        ]
        path='frozen/pizza/reviews.txt'
        branch = 'master'
        sha = '47b79b37ef1cf6f944f71ea13c6667ddd98b9804'
        permissions = {
            'view': True,
            'edit': True,
        }
        res = self.app.get(
            self.project.api_url_for(
                'gitlab_list_files',
                path=path, branch=branch, sha=sha
            ),
            auth=self.user.auth
        )
        expected = utils.gitlab_to_hgrid(
            self.project, mock_list.return_value, path=path,
            permissions=permissions, branch=branch, sha=sha
        )
        assert_equal(res.json, expected)
        mock_list.assert_called_with(
            self.node_settings.project_id, path=path,
            ref_name=sha
        )


class TestFileCommits(GitlabTestCase):

    @mock.patch('website.addons.gitlab.views.crud.client.listrepositorycommits')
    def test_commits_sha_given(self, mock_commits):
        mock_commits.return_value = [
            {
                'author_email': 'test94@test.test',
                'author_name': 'test test',
                'created_at': '2014-04-01T17:40:49+00:00',
                'id': '2e84e78b5dfdb4a72132e08c9684b0e1a7e97bc2',
                'short_id': '2e84e78b5df',
                'title': 'Added via the Open Science Framework'
            }
        ]
        path = 'frozen/pizza/review.txt'
        branch = 'master'
        sha = '2e84e78b5dfdb4a72132e08c9684b0e1a7e97bc2'
        guid = GitlabGuidFileFactory(
            node=self.project,
            path=path,
        )
        res = self.app.get(
            self.project.api_url_for(
                'gitlab_file_commits',
                path=path, branch=branch, sha=sha
            ),
            auth=self.user.auth,
        )
        serialized = [
            utils.serialize_commit(
                self.project, path, commit, guid, branch
            )
            for commit in mock_commits.return_value
        ]
        assert_equal(
            res.json,
            {
                'sha': sha,
                'commits': serialized,
            }
        )
        mock_commits.assert_called_with(
            self.node_settings.project_id,
            path=path, ref_name=branch
        )

    @mock.patch('website.addons.gitlab.views.crud.client.listrepositorycommits')
    def test_commits_sha_not_given(self, mock_commits):
        mock_commits.return_value = [
            {
                'author_email': 'test94@test.test',
                'author_name': 'test test',
                'created_at': '2014-04-01T17:40:49+00:00',
                'id': '2e84e78b5dfdb4a72132e08c9684b0e1a7e97bc2',
                'short_id': '2e84e78b5df',
                'title': 'Added via the Open Science Framework'
            }
        ]
        path = 'frozen/pizza/review.txt'
        branch = 'master'
        guid = GitlabGuidFileFactory(
            node=self.project,
            path=path,
        )
        res = self.app.get(
            self.project.api_url_for(
                'gitlab_file_commits',
                path=path, branch=branch
            ),
            auth=self.user.auth,
        )
        serialized = [
            utils.serialize_commit(
                self.project, path, commit, guid, branch
            )
            for commit in mock_commits.return_value
        ]
        assert_equal(
            res.json,
            {
                'sha': mock_commits.return_value[0]['id'],
                'commits': serialized,
            }
        )
        mock_commits.assert_called_with(
            self.node_settings.project_id,
            path=path, ref_name=branch,
        )


class TestDownloadFile(GitlabTestCase):

    @mock.patch('website.addons.gitlab.views.crud.fileservice.GitlabFileService.download')
    def test_download(self, mock_download):
        mock_download.return_value = 'pizza'
        path = 'pizza/reviews.rst'
        branch = 'master'
        res = self.app.get(
            self.project.web_url_for(
                'gitlab_download_file',
                path=path, branch=branch,
            ),
            auth=self.user.auth,
        )
        assert_equal(res.body, 'pizza')
        assert_equal(
            res.headers['Content-Disposition'],
            'attachment; filename=reviews.rst',
        )
        mock_download.assert_called_with(path, branch)

    @mock.patch('website.addons.gitlab.views.crud.fileservice.GitlabFileService.download')
    def test_download_not_found(self, mock_download):
        mock_download.side_effect = fileservice.FileDownloadError
        path = 'pizza/reviews.rst'
        branch = 'master'
        res = self.app.get(
            self.project.web_url_for(
                'gitlab_download_file',
                path=path, branch=branch
            ),
            auth=self.user.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, http.NOT_FOUND)


class TestDeleteFile(GitlabTestCase):

    @mock.patch('website.addons.gitlab.views.crud.fileservice.GitlabFileService.delete')
    def test_delete(self, mock_delete_file):
        path = 'frozen/pizza/reviews.txt'
        branch = 'develop'
        self.app.delete(
            self.project.api_url_for(
                'gitlab_delete_file',
                path=path, branch=branch,
            ),
            auth=self.user.auth,
        )
        self.project.reload()
        mock_delete_file.assert_called_with(path, branch)
        assert_equal(
            self.project.logs[-1].action,
            'gitlab_{0}'.format(NodeLog.FILE_REMOVED)
        )

    @mock.patch('website.addons.gitlab.views.crud.fileservice.GitlabFileService.delete')
    def test_delete_gitlab_error(self, mock_delete_file):
        mock_delete_file.side_effect = fileservice.FileDeleteError()
        path = 'frozen/pizza/reviews.txt'
        branch = 'develop'
        res = self.app.delete(
            self.project.api_url_for(
                'gitlab_delete_file',
                path=path, branch=branch,
            ),
            auth=self.user.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, http.BAD_REQUEST)


class TestUploadFile(GitlabTestCase):

    @mock.patch('website.addons.gitlab.views.crud.fileservice.GitlabFileService.upload')
    def test_upload_error(self, mock_upload):
        mock_upload.side_effect = fileservice.FileUploadError()
        payload = {'file': Upload('myfile.rst', 'baz')}
        res = self.app.post(
            self.project.api_url_for(
                'gitlab_upload_file',
                path='path', branch='master',
            ),
            payload,
            auth=self.user.auth,
        )
        assert_equal(
            res.json,
            {
                'actionTaken': None,
                'name': 'myfile.rst',
            }
        )
        self.project.reload()
        assert_not_in(
            self.project.logs[-1].action,
            [
                'gitlab_{0}'.format(NodeLog.FILE_ADDED),
                'gitlab_{0}'.format(NodeLog.FILE_UPDATED),
            ]
        )

    @mock.patch('website.addons.gitlab.views.crud.fileservice.GitlabFileService.upload')
    def test_upload_create(self, mock_upload):
        mock_upload.return_value = (
            NodeLog.FILE_ADDED,
            {'file_path': 'path'}
        )
        payload = {'file': Upload('myfile.rst', 'baz')}
        res = self.app.post(
            self.project.api_url_for(
                'gitlab_upload_file',
                path='path', branch='master',
            ),
            payload,
            auth=self.user.auth,
        )
        self.project.reload()
        assert_equal(res.status_code, http.CREATED)
        assert_equal(
            self.project.logs[-1].action,
            'gitlab_{0}'.format(NodeLog.FILE_ADDED),
        )

    @mock.patch('website.addons.gitlab.views.crud.fileservice.GitlabFileService.upload')
    def test_upload_update(self, mock_upload):
        mock_upload.return_value = (
            NodeLog.FILE_UPDATED,
            {'file_path': 'path'}
        )
        payload = {'file': Upload('myfile.rst', 'baz')}
        res = self.app.post(
            self.project.api_url_for(
                'gitlab_upload_file',
                path='path', branch='master',
            ),
            payload,
            auth=self.user.auth,
        )
        self.project.reload()
        assert_equal(res.status_code, http.OK)
        assert_equal(
            self.project.logs[-1].action,
            'gitlab_{0}'.format(NodeLog.FILE_UPDATED),
        )
