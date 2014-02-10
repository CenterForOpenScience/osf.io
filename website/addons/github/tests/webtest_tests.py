import mock
from nose.tools import *  # PEP8 asserts
from tests.base import DbTestCase
from tests.factories import ProjectFactory, AuthUserFactory
from website.addons.github.tests.utils import create_mock_github

from webtest_plus import TestApp
import website.app
app = website.app.init_app(
    routes=True, set_backends=False, settings_module='website.settings'
)


class TestGitHubFileView(DbTestCase):

    def setUp(self):
        self.user = AuthUserFactory()
        self.app = TestApp(app)
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('github')
        self.project.creator.add_addon('github')

        self.github = create_mock_github(user='fred', private=False)

        self.node_settings = self.project.get_addon('github')
        self.node_settings.user_settings = self.project.creator.get_addon('github')
        # Set the node addon settings to correspond to the values of the mock repo
        self.node_settings.user = self.github.repo.return_value['owner']['login']
        self.node_settings.repo = self.github.repo.return_value['name']
        self.node_settings.save()

    def test_can_see_files_tab(self):
        url = "/project/{0}/".format(self.project._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_in('a href="/{0}/files/"'.format(self.project._id), res)

    @mock.patch('website.addons.github.api.GitHub.commits')
    @mock.patch('website.addons.github.api.GitHub.file')
    @mock.patch('website.addons.github.api.GitHub.repo')
    def test_file_view(self, mock_repo, mock_file, mock_commits):
        mock_commits.return_value = [{
            "url": "https://api.github.com/repos/octocat/Hello-World/commits/6dcb09b5b57875f334f61aebed695e2e4193db5e",
            "sha": "6dcb09b5b57875f334f61aebed695e2e4193db5e",
            "commit": {
                "url": "https://api.github.com/repos/octocat/Hello-World/git/commits/6dcb09b5b57875f334f61aebed695e2e4193db5e",
                "author": {
                    "name": "Monalisa Octocat",
                    "email": "support@github.com",
                   "date": "2011-04-14T16:00:49Z"
                }
            }
        }]

        mock_repo.return_value = {
            "default_branch": "dev",
            'url': u'https://api.github.com/repos/{user}/mock-repo/git/trees/dev'.format(user=self.user),
            'sha': 'dev',
            'private': False,
            'tree': [
                {u'mode': u'100644',
                 u'path': u'coveragerc',
                 u'sha': u'92029ff5ce192425d346b598d7e7dd25f5f05185',
                 u'size': 245,
                 u'type': u'file',
                 u'url': u'https://api.github.com/repos/{user}/mock-repo/git/blobs/92029ff5ce192425d346b598d7e7dd25f5f05185'.format(user=self.user)}]
        }

        mock_file.return_value = {
            u'name': u'coveragerc',
            u'content': u'ClRleHRCbG9iOiBTaW1wbGlmaWVkIFRleHQgUHJvY2Vzc2luZwo9PT09PT09',
            u'size': 245
        }

        url = "/project/{0}/github/file/{1}/".format(
            self.project._id,
            "coveragerc"
        )
        self.app.auth = self.user.auth
        res = self.app.get(url).maybe_follow()
        assert_in("6dcb09b5b57875f334f61aebed695e2e4193db5e", res)
        assert_in("2011-04-14T16:00:49Z", res)
        assert_in("file-version-history", res)
        assert_in("icon-download-alt", res)
