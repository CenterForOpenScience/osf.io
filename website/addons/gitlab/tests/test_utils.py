import mock
import unittest
from nose.tools import *

import os
import urllib
import datetime
import urlparse

from tests.base import OsfTestCase, fake
from tests.factories import UserFactory

from framework.exceptions import HTTPError

from website.addons.base import AddonError
from website.dates import FILE_MODIFIED

from website.addons.gitlab.tests import GitlabTestCase
from website.addons.gitlab.tests.factories import GitlabGuidFileFactory

from website.addons.gitlab import settings as gitlab_settings
from website.addons.gitlab import utils
from website.addons.gitlab.api import GitlabError


def normalize_query_string(url):
    parsed = urlparse.urlparse(url)
    query_data = dict(urlparse.parse_qsl(parsed.query))
    query_str = urllib.urlencode(query_data)
    return parsed._replace(query=query_str).geturl()


def assert_urls_equal(url1, url2):
    assert_equal(
        normalize_query_string(url1),
        normalize_query_string(url2)
    )


class TestTranslatePermissions(unittest.TestCase):

    def test_translate_admin(self):
        assert_equal(
            utils.translate_permissions(['read', 'write', 'admin']),
            'master'
        )

    def test_translate_write(self):
        assert_equal(
            utils.translate_permissions(['read', 'write']),
            'developer'
        )

    def test_translate_read(self):
        assert_equal(
            utils.translate_permissions(['read']),
            'reporter'
        )


class TestKwargsToPath(unittest.TestCase):

    def test_kwargs_to_path(self):
        assert_equal(
            utils.kwargs_to_path({'path': 'foo/bar/baz'}),
            urllib.unquote_plus('foo/bar/baz')
        )

    def test_kwargs_to_path_required(self):
        with assert_raises(HTTPError):
            utils.kwargs_to_path({}, required=True)


class TestRefsToParams(unittest.TestCase):

    def test_no_kwargs(self):
        assert_equal(
            utils.refs_to_params(),
            ''
        )

    def test_branch(self):
        assert_equal(
            utils.refs_to_params(branch='master'),
            '?' + urllib.urlencode({'branch': 'master'})
        )

    def test_sha(self):
        assert_equal(
            utils.refs_to_params(sha='12345'),
            '?' + urllib.urlencode({'sha': '12345'})
        )

    def test_branch_sha(self):
        assert_equal(
            utils.refs_to_params(branch='master', sha='12345'),
            '?' + urllib.urlencode({'branch': 'master', 'sha': '12345'})
        )


class TestSlugify(unittest.TestCase):

    def test_replace_special(self):
        assert_equal(
            utils.gitlab_slugify('foo&bar_baz'),
            'foo-bar-baz'
        )

    def test_replace_git(self):
        assert_equal(
            utils.gitlab_slugify('foo.git'),
            'foo'
        )


class TestBuildUrls(GitlabTestCase):

    def test_tree(self):

        item = {
            'name': 'foo',
            'type': 'tree',
        }
        path = 'myfolder'
        branch = 'master'
        sha = '12345'

        output = utils.build_full_urls(
            self.project, item, path, branch, sha
        )

        quote_path = urllib.quote_plus(path)

        assert_equal(
            set(output.keys()),
            {'upload', 'fetch', 'root'}
        )
        assert_urls_equal(
            output['upload'],
            self.node_lookup(
                'api', 'gitlab_upload_file',
                path=quote_path, branch=branch
            )
        )
        assert_urls_equal(
            output['fetch'],
            self.node_lookup(
                'api', 'gitlab_list_files',
                path=quote_path, branch=branch, sha=sha
            )
        )

    def test_blob(self):

        item = {
            'name': 'bar',
            'type': 'blob',
        }
        path = 'myfolder'
        branch = 'master'
        sha = '12345'

        output = utils.build_full_urls(
            self.project, item, path, branch, sha
        )

        quote_path = urllib.quote_plus(path)

        assert_equal(
            set(output.keys()),
            {'view', 'download', 'delete', 'render'}
        )
        assert_urls_equal(
            output['view'],
            self.node_lookup(
                'web', 'gitlab_view_file',
                path=quote_path, branch=branch, sha=sha
            )
        )
        assert_urls_equal(
            output['download'],
            self.node_lookup(
                'web', 'gitlab_download_file',
                path=quote_path, branch=branch, sha=sha
            )
        )
        assert_urls_equal(
            output['delete'],
            self.node_lookup(
                'api', 'gitlab_delete_file',
                path=quote_path, branch=branch
            )
        )

    def test_bad_type(self):
        with assert_raises(ValueError):
            utils.build_full_urls(
                self.project, item={'type': 'bad'}, path=''
            )


class TestGridSerializers(GitlabTestCase):

    def test_item_to_hgrid(self):

        item = {
            'name': 'myfile',
            'type': 'blob',
        }
        path = 'myfolder'
        permissions = {
            'view': True,
            'edit': True,
        }

        output = utils.item_to_hgrid(
            self.project, item, path, permissions
        )

        assert_equal(output['name'], 'myfile')
        assert_equal(output['kind'], utils.type_to_kind['blob'])
        assert_equal(output['permissions'], permissions)
        assert_equal(
            output['urls'],
            utils.build_full_urls(
                self.project, item, os.path.join(path, item['name'])
            )
        )


class TestSetupUser(GitlabTestCase):

    def setUp(self):
        super(TestSetupUser, self).setUp()
        self.user_settings.user_id = None

    @mock.patch('website.addons.gitlab.utils.client.createuser')
    def test_setup_user(self, mock_create_user):
        mock_create_user.return_value = {
            'id': 1,
            'username': 'freddie'
        }
        utils.setup_user(self.user)
        mock_create_user.assert_called_with(
            name=self.user.fullname,
            username=self.user._id,
            password=None,
            email=self.user.username,
            encrypted_password=self.user.password,
            skip_confirmation=True,
            projects_limit=gitlab_settings.PROJECTS_LIMIT,
        )
        assert_equal(self.user_settings.user_id, 1)
        assert_equal(self.user_settings.username, 'freddie')

    @mock.patch('website.addons.gitlab.utils.client.createuser')
    def test_setup_user_gitlab_error(self, mock_create_user):
        mock_create_user.side_effect = GitlabError('Failed')
        with assert_raises(AddonError):
            utils.setup_user(self.user)

    @mock.patch('website.addons.gitlab.utils.client.createuser')
    def test_setup_user_already_exists(self, mock_create_user):
        self.user_settings.user_id = 1
        utils.setup_user(self.user)
        assert_false(mock_create_user.called)


class TestSetupNode(GitlabTestCase):

    def setUp(self):
        super(TestSetupNode, self).setUp()
        self.node_settings.project_id = None

    @mock.patch('website.addons.gitlab.utils.hookservice.GitlabHookService.create')
    @mock.patch('website.addons.gitlab.utils.client.createprojectuser')
    def test_setup_node(self, mock_create_project, mock_create_hook):
        mock_create_project.return_value = {
            'id': 1,
        }
        utils.setup_node(self.project)
        mock_create_project.assert_called_with(
            self.user_settings.user_id, self.project._id
        )
        mock_create_hook.assert_called_with(save=True)

    @mock.patch('website.addons.gitlab.utils.client.createprojectuser')
    def test_setup_node_gitlab_error(self, mock_create_node):
        mock_create_node.side_effect = GitlabError('Failed')
        with assert_raises(AddonError):
            utils.setup_node(self.project)

    @mock.patch('website.addons.gitlab.utils.client.createprojectuser')
    def test_setup_node_already_exists(self, mock_create_project):
        self.node_settings.project_id = 1
        utils.setup_node(self.project)
        assert_false(mock_create_project.called)


class TestResolveGitlabCommitAuthor(OsfTestCase):

    def setUp(self):
        super(TestResolveGitlabCommitAuthor, self).setUp()
        self.user = UserFactory()

    def test_osf_user(self):
        commit = {
            'author_name': self.user.fullname,
            'author_email': self.user.username,
        }
        author = utils.resolve_gitlab_commit_author(commit)
        assert_equal(
            author,
            {
                'name': self.user.fullname,
                'url': self.user.url,
            }
        )

    def test_not_osf_user(self):
        name, email = fake.name(), fake.email()
        commit = {
            'author_name': name,
            'author_email': email,
        }
        author = utils.resolve_gitlab_commit_author(commit)
        assert_equal(
            author,
            {
                'name': name,
                'url': 'mailto:{0}'.format(email)
            }
        )


class TestResolveGitlabHookAuthor(OsfTestCase):

    def setUp(self):
        super(TestResolveGitlabHookAuthor, self).setUp()
        self.user = UserFactory()

    def test_resolve_to_user(self):
        author = {
            'name': self.user.fullname,
            'email': self.user.username,
        }
        user = utils.resolve_gitlab_hook_author(author)
        assert_equal(user, self.user)

    def test_resolve_to_name(self):
        author = {
            'name': 'Gitlab User',
            'email': 'git@gitlab.com',
        }
        user = utils.resolve_gitlab_hook_author(author)
        assert_equal(user, 'Gitlab User')


class TestSerializeCommit(GitlabTestCase):

    def setUp(self):
        super(TestSerializeCommit, self).setUp()
        self.user = UserFactory()

    def test_serialize_commit(self):
        now = datetime.datetime.now()
        path = 'pizza/review.rst'
        commit = {
            'id': '0c015ac47ee16eb0fc17c0a6417d57622bbf142d',
            'created_at': now.isoformat(),
            'author_name': 'Freddie Mercury',
            'author_email': 'freddie@queen.com',
        }
        guid = GitlabGuidFileFactory()
        branch = 'master'
        serialized = utils.serialize_commit(
            self.project, path, commit, guid, branch
        )
        params = utils.refs_to_params(branch=branch, sha=commit['id'])
        assert_equal(
            serialized,
            {
                'sha': '0c015ac47ee16eb0fc17c0a6417d57622bbf142d',
                'date': now.strftime(FILE_MODIFIED),
                'committer': utils.resolve_gitlab_commit_author(commit),
                'downloads': 0,
                'urls': {
                    'view': '/' + guid._id + '/' + params,
                    'download': '/' + guid._id + '/download/' + params,
                }
            }
        )

class TestRefOrDefault(GitlabTestCase):

    def test_get_ref_branch_and_sha(self):
        ref = utils.ref_or_default(
            self.node_settings,
            {
                'sha': '47b79b37ef1cf6f944f71ea13c6667ddd98b9804',
                'branch': 'master',
            }
        )
        assert_equal(ref, '47b79b37ef1cf6f944f71ea13c6667ddd98b9804')

    def test_get_ref_branch(self):
        ref = utils.ref_or_default(self.node_settings, {'branch': 'master'})
        assert_equal(ref, 'master')

    @mock.patch('website.addons.gitlab.utils.client.getproject')
    def test_get_ref_project_id(self, mock_get_project):
        mock_get_project.return_value = {
            'default_branch': 'master',
        }
        ref = utils.ref_or_default(self.node_settings, {})
        assert_equal(ref, 'master')

    def test_get_ref_no_id_no_refs(self):
        self.node_settings.project_id = None
        with assert_raises(AddonError):
            utils.ref_or_default(self.node_settings, {})

class TestDefaultRefs(GitlabTestCase):

    @mock.patch('website.addons.gitlab.utils.client.getproject')
    def test_get_default_branch(self, mock_get_project):
        mock_get_project.return_value = {
            'default_branch': 'master',
        }
        assert_equal(
            utils.get_default_branch(self.node_settings),
            'master'
        )

    @mock.patch('website.addons.gitlab.utils.client.listrepositorycommits')
    def test_get_default_file_sha(self, mock_commits):
        mock_commits.return_value = [
            {
                'id': '47b79b37ef1cf6f944f71ea13c6667ddd98b9804',
            }
        ]
        utils.get_default_file_sha(
            self.node_settings,
            'pizza.py', branch='master',
        )
        mock_commits.assert_called_with(
            self.node_settings.project_id,
            ref_name='master', path='pizza.py',
        )

    def test_get_default_file_sha_no_project_id(self):
        self.node_settings.project_id = None
        with assert_raises(AddonError):
            utils.get_default_file_sha(self.node_settings, path='pizza.py')

    @mock.patch('website.addons.gitlab.utils.client.listbranch')
    def test_get_branch_id(self, mock_list_branch):
        mock_list_branch.return_value = {
            'name': 'master',
            'commit': {
                'id': '47b79b37ef1cf6f944f71ea13c6667ddd98b9804',
            }
        }
        assert_equal(
            utils.get_branch_id(self.node_settings, 'master'),
            '47b79b37ef1cf6f944f71ea13c6667ddd98b9804'
        )

    @mock.patch('website.addons.gitlab.utils.client.listbranches')
    def test_get_default_branch_and_sha_one_branch(self, mock_list_branches):
        mock_list_branches.return_value = [
            {
                'name': 'master',
                'commit': {
                    'id': '47b79b37ef1cf6f944f71ea13c6667ddd98b9804',
                }
            }
        ]
        assert_equal(
            utils.get_default_branch_and_sha(self.node_settings),
            ('master', '47b79b37ef1cf6f944f71ea13c6667ddd98b9804')
        )

    @mock.patch('website.addons.gitlab.utils.client.getproject')
    @mock.patch('website.addons.gitlab.utils.client.listbranches')
    def test_get_default_branch_and_sha_multi_branch(self, mock_list_branches, mock_get_project):
        mock_list_branches.return_value = [
            {
                'name': 'master',
                'commit': {
                    'id': '47b79b37ef1cf6f944f71ea13c6667ddd98b9804',
                }
            },
            {
                'name': 'develop',
                'commit': {
                    'id': '0c015ac47ee16eb0fc17c0a6417d57622bbf142d',
                }
            }
        ]
        mock_get_project.return_value = {
            'default_branch': 'develop',
        }
        assert_equal(
            utils.get_default_branch_and_sha(self.node_settings),
            ('develop', '0c015ac47ee16eb0fc17c0a6417d57622bbf142d')
        )

    @mock.patch('website.addons.gitlab.utils.client.getproject')
    @mock.patch('website.addons.gitlab.utils.client.listbranches')
    def test_get_default_branch_and_sha_multi_branch_not_found(self, mock_list_branches, mock_get_project):
        mock_list_branches.return_value = [
            {
                'name': 'master',
                'commit': {
                    'id': '47b79b37ef1cf6f944f71ea13c6667ddd98b9804',
                }
            },
            {
                'name': 'develop',
                'commit': {
                    'id': '0c015ac47ee16eb0fc17c0a6417d57622bbf142d',
                }
            }
        ]
        mock_get_project.return_value = {
            'default_branch': 'feature/gitlab',
        }
        with assert_raises(AddonError):
            utils.get_default_branch_and_sha(self.node_settings)

    def test_get_branch_and_sha_both_provided(self):
        assert_equal(
            utils.get_branch_and_sha(
                self.node_settings,
                {
                    'branch': 'master',
                    'sha': '47b79b37ef1cf6f944f71ea13c6667ddd98b9804',
                }
            ),
            ('master', '47b79b37ef1cf6f944f71ea13c6667ddd98b9804')
        )

    @mock.patch('website.addons.gitlab.utils.get_branch_id')
    def test_get_branch_and_sha_branch_provided(self, mock_branch_id):
        mock_branch_id.return_value = '47b79b37ef1cf6f944f71ea13c6667ddd98b9804'
        assert_equal(
            utils.get_branch_and_sha(
                self.node_settings,
                {
                    'branch': 'master',
                }
            ),
            ('master', '47b79b37ef1cf6f944f71ea13c6667ddd98b9804')
        )

    def test_get_branch_and_sha_sha_provided(self):
        with assert_raises(ValueError):
            utils.get_branch_and_sha(
                self.node_settings,
                {
                    'sha': '2e84e78b5dfdb4a72132e08c9684b0e1a7e97bc2'
                }
            )

    @mock.patch('website.addons.gitlab.utils.get_default_branch_and_sha')
    def test_get_branch_and_sha_none_provided(self, mock_defaults):
        mock_defaults.return_value = (
            'master', '2e84e78b5dfdb4a72132e08c9684b0e1a7e97bc2'
        )
        assert_equal(
            utils.get_branch_and_sha(self.node_settings, {}),
            mock_defaults.return_value
        )
