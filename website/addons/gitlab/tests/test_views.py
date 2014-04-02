import mock
from nose.tools import *

from tests.base import fake

from website.addons.gitlab import settings as gitlab_settings
from website.addons.gitlab.views import hooks
from website.addons.gitlab import utils

from website.addons.gitlab.tests import GitlabTestCase
from website.addons.gitlab.tests.factories import GitlabGuidFileFactory


class TestHookLog(GitlabTestCase):

    def test_add_log_from_osf(self):
        log_count = len(self.project.logs)
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
        self.project.reload()
        assert_equal(
            len(self.project.logs),
            log_count
        )

    def test_add_log_from_osf_user(self):
        log_count = len(self.project.logs)
        payload = {
            'id': '47b79b37ef1cf6f944f71ea13c6667ddd98b9804',
            'message': 'pushed from git',
            'timestamp': '2014-03-31T13:40:39+00:00',
            'author': {
                'name': self.user.fullname,
                'email': self.user.username,
            }
        }
        hooks.add_hook_log(self.node_settings, payload, save=True)
        self.project.reload()
        assert_equal(
            len(self.project.logs),
            log_count + 1
        )
        assert_equal(self.project.logs[-1].user, self.user)
        assert_equal(self.project.logs[-1].foreign_user,  None)

    def test_add_log_from_non_osf_user(self):
        name, email = fake.name(), fake.email()
        log_count = len(self.project.logs)
        payload = {
            'id': '47b79b37ef1cf6f944f71ea13c6667ddd98b9804',
            'message': 'pushed from git',
            'timestamp': '2014-03-31T13:40:39+00:00',
            'author': {
                'name': name,
                'email': email,
            }
        }
        hooks.add_hook_log(self.node_settings, payload, save=True)
        self.project.reload()
        assert_equal(
            len(self.project.logs),
            log_count + 1
        )
        assert_equal(self.project.logs[-1].user, None)
        assert_equal(self.project.logs[-1].foreign_user, name)


class TestListFiles(GitlabTestCase):

    def setUp(self):
        super(TestListFiles, self).setUp()
        self.app.app.test_request_context().push()

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

    def setUp(self):
        super(TestFileCommits, self).setUp()
        self.app.app.test_request_context().push()

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
            auth=self.user.auth
        )
        serialized = [
            utils.serialize_commit(
                commit, guid, branch
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
            auth=self.user.auth
        )
        serialized = [
            utils.serialize_commit(
                commit, guid, branch
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
            path=path, ref_name=branch
        )


# TODO: Write me @jmcarp
class TestDownloadFile(GitlabTestCase):

    def setUp(self):
        super(TestDownloadFile, self).setUp()
        self.app.app.test_request_context().push()

    def test_download_not_found(self):
        pass

    def test_download(self):
        pass
