import abc
from json import dumps

from unittest import mock
import pytest
import mendeley
from github3.repos import Repository
from github3.session import GitHubSession

from addons.bitbucket.tests.factories import BitbucketAccountFactory, BitbucketNodeSettingsFactory
from addons.box.tests.factories import BoxAccountFactory, BoxNodeSettingsFactory
from addons.dataverse.tests.factories import DataverseAccountFactory, DataverseNodeSettingsFactory
from addons.dropbox.tests.factories import DropboxAccountFactory, DropboxNodeSettingsFactory
from addons.github.tests.factories import GitHubAccountFactory, GitHubNodeSettingsFactory
from addons.googledrive.tests.factories import GoogleDriveAccountFactory, GoogleDriveNodeSettingsFactory
from addons.owncloud.tests.factories import OwnCloudAccountFactory, OwnCloudNodeSettingsFactory
from addons.s3.tests.factories import S3AccountFactory, S3NodeSettingsFactory
from addons.figshare.tests.factories import FigshareAccountFactory, FigshareNodeSettingsFactory
from api.base.settings.defaults import API_BASE
from osf_tests.factories import AuthUserFactory
from tests.base import ApiAddonTestCase

from addons.mendeley.tests.factories import (
    MendeleyAccountFactory, MendeleyNodeSettingsFactory
)
from addons.zotero.tests.factories import (
    ZoteroAccountFactory, ZoteroNodeSettingsFactory
)
from osf.utils.permissions import WRITE, READ, ADMIN

pytestmark = pytest.mark.django_db
# Varies between addons. Some need to make a call to get the root,
# 'FAKEROOTID' should be the result of a mocked call in that case.
VALID_ROOT_FOLDER_IDS = (
    '/',
    '0',
    'FAKEROOTID',
)


class NodeAddonListMixin:
    def set_setting_list_url(self):
        self.setting_list_url = '/{}nodes/{}/addons/?page[size]=100'.format(
            API_BASE, self.node._id
        )

    def get_response_for_addon(self, response):
        for datum in response.json['data']:
            if datum['id'] == self.short_name:
                return datum['attributes']
        return None

    def test_settings_list_GET_enabled(self):
        wrong_type = self.should_expect_errors()
        res = self.app.get(
            self.setting_list_url,
            auth=self.user.auth)

        addon_data = self.get_response_for_addon(res)
        if not wrong_type:
            assert self.account_id == addon_data['external_account_id']
            assert self.node_settings.has_auth == addon_data['node_has_auth']
            assert self.node_settings.folder_id == addon_data['folder_id']
        if wrong_type:
            assert addon_data is None

    def test_settings_list_GET_disabled(self):
        wrong_type = self.should_expect_errors()
        try:
            self.node.delete_addon(self.short_name, auth=self.auth)
        except ValueError:
            # If addon was mandatory -- OSFStorage
            pass
        res = self.app.get(
            self.setting_list_url,
            auth=self.user.auth,
            expect_errors=wrong_type)
        addon_data = self.get_response_for_addon(res)
        assert addon_data is None

    def test_settings_list_raises_error_if_PUT(self):
        res = self.app.put_json_api(
            self.setting_list_url,
            {'id': self.short_name, 'type': 'node-addons'},
            auth=self.user.auth, expect_errors=True
        )
        assert res.status_code == 405

    def test_settings_list_raises_error_if_PATCH(self):
        res = self.app.patch_json_api(
            self.setting_list_url,
            {'id': self.short_name, 'type': 'node-addons'},
            auth=self.user.auth, expect_errors=True)
        assert res.status_code == 405

    def test_settings_list_raises_error_if_DELETE(self):
        res = self.app.delete(
            self.setting_list_url,
            auth=self.user.auth, expect_errors=True)
        assert res.status_code == 405

    def test_settings_list_raises_error_if_noncontrib_not_public(self):
        noncontrib = AuthUserFactory()
        res = self.app.get(
            self.setting_list_url,
            auth=noncontrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    def test_settings_list_noncontrib_public_can_view(self):
        self.node.set_privacy('public', auth=self.auth)
        wrong_type = self.should_expect_errors()
        noncontrib = AuthUserFactory()
        res = self.app.get(
            self.setting_list_url,
            auth=noncontrib.auth)
        addon_data = self.get_response_for_addon(res)
        if not wrong_type:
            assert self.account_id == addon_data['external_account_id']
            assert self.node_settings.has_auth == addon_data['node_has_auth']
            assert self.node_settings.folder_id == addon_data['folder_id']
        if wrong_type:
            assert addon_data is None


class NodeAddonDetailMixin:
    def set_setting_detail_url(self):
        self.setting_detail_url = '/{}nodes/{}/addons/{}/'.format(
            API_BASE, self.node._id, self.short_name
        )

    def test_settings_detail_GET_enabled(self):
        wrong_type = self.should_expect_errors()
        res = self.app.get(
            self.setting_detail_url,
            auth=self.user.auth,
            expect_errors=wrong_type)

        if not wrong_type:
            addon_data = res.json['data']['attributes']
            assert self.account_id == addon_data['external_account_id']
            assert self.node_settings.has_auth == addon_data['node_has_auth']
            assert self.node_settings.folder_id == addon_data['folder_id']
        if wrong_type:
            assert res.status_code == 404

    def test_settings_detail_GET_disabled(self):
        try:
            self.node.delete_addon(self.short_name, auth=self.auth)
        except ValueError:
            # If addon was mandatory -- OSFStorage
            pass
        res = self.app.get(
            self.setting_detail_url,
            auth=self.user.auth,
            expect_errors=True)
        assert res.status_code == 404

    def test_settings_detail_PUT_all_sets_settings(self):
        wrong_type = self.should_expect_errors(
            success_types=('CONFIGURABLE', ))
        try:
            self.node_settings.deauthorize(auth=self.auth)
            self.node_settings.save()
        except (ValueError, AttributeError):
            # If addon was mandatory or non-configurable -- OSFStorage, Wiki
            pass
        data = {
            'data': {
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'external_account_id': self.account_id,
                }
            }
        }
        data['data']['attributes'].update(self._mock_folder_info)
        res = self.app.put_json_api(
            self.setting_detail_url,
            data, auth=self.user.auth,
            expect_errors=wrong_type)
        if not wrong_type:
            addon_data = res.json['data']['attributes']
            assert addon_data['external_account_id'] == self.account_id
            assert addon_data['folder_id'] == '0987654321'
            assert addon_data['node_has_auth']
        if wrong_type:
            assert res.status_code in [404, 501]

    def test_settings_detail_PUT_none_and_enabled_clears_settings(self):
        wrong_type = self.should_expect_errors(
            success_types=('CONFIGURABLE', ))
        res = self.app.put_json_api(
            self.setting_detail_url,
            {'data': {
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'external_account_id': None,
                    'folder_id': None
                }
            }},
            auth=self.user.auth,
            expect_errors=wrong_type)
        if not wrong_type:
            addon_data = res.json['data']['attributes']
            assert addon_data['external_account_id'] is None
            assert addon_data['folder_id'] is None
            assert not addon_data['node_has_auth']
        if wrong_type:
            assert res.status_code in [404, 501]

    def test_settings_detail_PUT_none_and_disabled_deauthorizes(self):
        wrong_type = self.should_expect_errors(
            success_types=('CONFIGURABLE', ))
        res = self.app.put_json_api(
            self.setting_detail_url,
            {'data': {
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'external_account_id': None,
                    'folder_id': None
                }
            }},
            auth=self.user.auth,
            expect_errors=wrong_type)
        if not wrong_type:
            addon_data = res.json['data']['attributes']
            assert addon_data['external_account_id'] is None
            assert addon_data['folder_id'] is None
            assert not addon_data['node_has_auth']
        if wrong_type:
            assert res.status_code in [404, 501]

    def test_settings_detail_DELETE_disables(self):
        wrong_type = self.should_expect_errors()
        res = self.app.delete(
            self.setting_detail_url,
            auth=self.user.auth,
            expect_errors=wrong_type)
        if not wrong_type:
            assert res.status_code == 204
            self.node.reload()
            assert not self.node.has_addon(self.short_name)
        if wrong_type:
            assert res.status_code in [404, 405]

    def test_settings_detail_POST_enables(self):
        wrong_type = self.should_expect_errors()
        try:
            self.node.delete_addon(self.short_name, auth=self.auth)
        except ValueError:
            # If addon was mandatory -- OSFStorage
            pass
        res = self.app.post_json_api(
            self.setting_detail_url, {
                'data': {
                    'id': self.short_name,
                    'type': 'node_addons',
                    'attributes': {}
                }
            },
            auth=self.user.auth,
            expect_errors=wrong_type)
        if not wrong_type:
            addon_data = res.json['data']['attributes']
            assert addon_data['external_account_id'] is None
            assert addon_data['folder_id'] is None
            assert not addon_data['node_has_auth']
        if wrong_type:
            assert res.status_code in [404, 405]

    def test_settings_detail_PATCH_to_enable_and_add_external_account_id(self):
        wrong_type = self.should_expect_errors(
            success_types=('CONFIGURABLE', ))
        try:
            self.node_settings.deauthorize(auth=self.auth)
            self.node_settings.save()
        except (ValueError, AttributeError):
            # If addon was mandatory or non-configurable -- OSFStorage, Wiki
            pass
        res = self.app.patch_json_api(
            self.setting_detail_url,
            {'data': {
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'external_account_id': self.account_id,
                }
            }},
            auth=self.user.auth,
            expect_errors=wrong_type)
        if not wrong_type:
            addon_data = res.json['data']['attributes']
            assert addon_data['external_account_id'] == self.account_id
            assert addon_data['folder_id'] is None
            assert addon_data['node_has_auth']
        if wrong_type:
            assert res.status_code in [404, 501]

    def test_settings_detail_PATCH_to_remove_external_account_id(self):
        wrong_type = self.should_expect_errors(
            success_types=('CONFIGURABLE', ))
        res = self.app.patch_json_api(
            self.setting_detail_url,
            {'data': {
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'external_account_id': None,
                }
            }
            },
            auth=self.user.auth,
            expect_errors=wrong_type)
        if not wrong_type:
            addon_data = res.json['data']['attributes']
            assert addon_data['external_account_id'] is None
            assert addon_data['folder_id'] is None
            assert not addon_data['node_has_auth']
        if wrong_type:
            assert res.status_code in [404, 501]

    def test_settings_detail_PATCH_to_add_folder_without_auth_conflict(self):
        wrong_type = self.should_expect_errors(
            success_types=('CONFIGURABLE', ))
        try:
            self.node_settings.deauthorize(self.auth)
            self.node_settings.save()
        except (ValueError, AttributeError):
            # If addon was mandatory or non-configurable -- OSFStorage, Wiki
            pass

        data = {
            'data': {
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {}
            }
        }
        data['data']['attributes'].update(self._mock_folder_info)
        res = self.app.patch_json_api(
            self.setting_detail_url,
            data, auth=self.user.auth,
            expect_errors=True
        )
        if not wrong_type:
            assert res.status_code == 409
            assert 'Cannot set folder without authorization' == res.json['errors'][0]['detail']
        if wrong_type:
            assert res.status_code in [404, 501]

    def test_settings_detail_PATCH_readcontrib_raises_error(self):
        read_user = AuthUserFactory()
        self.node.add_contributor(
            read_user, permissions=READ, auth=self.auth)
        res = self.app.patch_json_api(
            self.setting_detail_url,
            {'data': {
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'external_account_id': None,
                }
            }},
            auth=read_user.auth,
            expect_errors=True)
        assert res.status_code == 403

    def test_settings_detail_DELETE_success(self):
        wrong_type = self.should_expect_errors()
        res = self.app.delete(
            self.setting_detail_url,
            auth=self.user.auth,
            expect_errors=True)
        if not wrong_type:
            assert res.status_code == 204
        else:
            assert res.status_code == 404

    def test_settings_detail_raises_error_if_DELETE_not_enabled(self):
        try:
            self.node.delete_addon(self.short_name, auth=self.auth)
        except ValueError:
            # If addon was mandatory -- OSFStorage
            pass
        res = self.app.delete(
            self.setting_detail_url,
            auth=self.user.auth,
            expect_errors=True)
        assert res.status_code == 404

    def test_settings_detail_raises_error_if_POST_already_configured(self):
        wrong_type = self.should_expect_errors()
        res = self.app.post_json_api(
            self.setting_detail_url,
            {'data': {
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {}
            }},
            auth=self.user.auth,
            expect_errors=True)
        if not wrong_type:
            assert res.status_code == 400
            assert 'already enabled' in res.body.decode()
        else:
            assert res.status_code == 404

    def test_settings_detail_raises_error_if_noncontrib_not_public_GET(self):
        noncontrib = AuthUserFactory()
        res = self.app.get(
            self.setting_detail_url,
            auth=noncontrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    def test_settings_detail_raises_error_if_noncontrib_not_public_PUT(self):
        noncontrib = AuthUserFactory()
        res = self.app.put_json_api(
            self.setting_detail_url,
            {'data': {
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'external_account_id': None,
                    'folder_id': None,
                }
            }},
            auth=noncontrib.auth, expect_errors=True)
        assert res.status_code == 403

    def test_settings_detail_raises_error_if_noncontrib_not_public_PATCH(self):
        noncontrib = AuthUserFactory()
        res = self.app.patch_json_api(
            self.setting_detail_url,
            {'data': {
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'external_account_id': None
                }
            }},
            auth=noncontrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    def test_settings_detail_noncontrib_public_can_view(self):
        self.node.set_privacy('public', auth=self.auth)
        noncontrib = AuthUserFactory()
        wrong_type = self.should_expect_errors()
        res = self.app.get(
            self.setting_detail_url,
            auth=noncontrib.auth,
            expect_errors=wrong_type)

        if not wrong_type:
            assert res.status_code == 200
            addon_data = res.json['data']['attributes']
            assert self.account_id == addon_data['external_account_id']
            assert self.node_settings.has_auth == addon_data['node_has_auth']
            assert self.node_settings.folder_id == addon_data['folder_id']
        if wrong_type:
            assert res.status_code == 404

    def test_settings_detail_noncontrib_public_cannot_edit(self):
        self.node.set_privacy('public', auth=self.auth)
        noncontrib = AuthUserFactory()
        res = self.app.patch_json_api(
            self.setting_detail_url,
            {'data': {
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'external_account_id': None
                }
            }},
            auth=noncontrib.auth,
            expect_errors=True)
        assert res.status_code == 403


class NodeAddonFolderMixin:
    def set_folder_url(self):
        self.folder_url = '/{}nodes/{}/addons/{}/folders/'.format(
            API_BASE, self.node._id, self.short_name
        )

    def test_folder_list_GET_expected_behavior(self):
        wrong_type = self.should_expect_errors(
            success_types=('CONFIGURABLE', ))
        res = self.app.get(
            self.folder_url,
            auth=self.user.auth,
            expect_errors=wrong_type)

        if not wrong_type:
            addon_data = res.json['data'][0]['attributes']
            assert addon_data['kind'] in ('folder', 'repo')
            assert addon_data['name'] == self._mock_folder_result['name']
            assert addon_data['path'] == self._mock_folder_result['path']
            assert addon_data['folder_id'] == self._mock_folder_result['id']
        if wrong_type:
            assert res.status_code in [404, 501]

    def test_folder_list_raises_error_if_PUT(self):
        res = self.app.put_json_api(
            self.folder_url,
            {'id': self.short_name, 'type': 'node-addon-folders'},
            auth=self.user.auth, expect_errors=True
        )
        assert res.status_code == 405

    def test_folder_list_raises_error_if_PATCH(self):
        res = self.app.patch_json_api(
            self.folder_url,
            {'id': self.short_name, 'type': 'node-addon-folders'},
            auth=self.user.auth, expect_errors=True
        )
        assert res.status_code == 405

    def test_folder_list_raises_error_if_DELETE(self):
        res = self.app.delete(
            self.folder_url,
            auth=self.user.auth,
            expect_errors=True)
        assert res.status_code == 405

    def test_folder_list_GET_raises_error_noncontrib_not_public(self):
        noncontrib = AuthUserFactory()
        res = self.app.get(
            self.folder_url,
            auth=noncontrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    def test_folder_list_GET_raises_error_writecontrib_not_authorizer(self):
        wrong_type = self.should_expect_errors()
        write_user = AuthUserFactory()
        self.node.add_contributor(
            write_user,
            permissions=WRITE,
            auth=self.auth)
        res = self.app.get(
            self.folder_url,
            auth=write_user.auth,
            expect_errors=True)
        if wrong_type:
            assert res.status_code in [404, 501]
        else:
            assert res.status_code == 403

    def test_folder_list_GET_raises_error_admin_not_authorizer(self):
        wrong_type = self.should_expect_errors()
        admin_user = AuthUserFactory()
        self.node.add_contributor(
            admin_user, permissions=ADMIN,
            auth=self.auth)
        res = self.app.get(
            self.folder_url,
            auth=admin_user.auth,
            expect_errors=True)
        if not wrong_type:
            assert res.status_code == 403
        else:
            assert res.status_code in [404, 501]


class NodeAddonTestSuiteMixin(
        NodeAddonListMixin,
        NodeAddonDetailMixin,
        NodeAddonFolderMixin):
    def set_urls(self):
        self.set_setting_list_url()
        self.set_setting_detail_url()
        self.set_folder_url()

    def should_expect_errors(self, success_types=('CONFIGURABLE', 'OAUTH')):
        return self.addon_type not in success_types

    @property
    def _mock_folder_info(self):
        return {'folder_id': '0987654321'}


class NodeOAuthAddonTestSuiteMixin(NodeAddonTestSuiteMixin):
    addon_type = 'OAUTH'

    @property
    @abc.abstractmethod
    def AccountFactory(self):
        pass

    @property
    @abc.abstractmethod
    def NodeSettingsFactory(self):
        pass

    def _apply_auth_configuration(self, *args, **kwargs):
        settings = self._settings_kwargs(self.node, self.user_settings)
        for key in settings:
            setattr(self.node_settings, key, settings[key])
        self.node_settings.external_account = self.account
        self.node_settings.save()


class NodeConfigurableAddonTestSuiteMixin(NodeOAuthAddonTestSuiteMixin):
    addon_type = 'CONFIGURABLE'


class NodeOAuthCitationAddonTestSuiteMixin(NodeOAuthAddonTestSuiteMixin):
    def _settings_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'list_id': 'fake_folder_id',
            'owner': self.node
        }

    def test_settings_list_noncontrib_public_can_view(self):
        with mock.patch.object(self.node_settings.__class__, '_fetch_folder_name', return_value='fake_folder'):
            super().test_settings_list_noncontrib_public_can_view

    def test_settings_list_GET_enabled(self):
        with mock.patch.object(self.node_settings.__class__, '_fetch_folder_name', return_value='fake_folder'):
            super().test_settings_list_GET_enabled

    def test_settings_detail_noncontrib_public_can_view(self):
        with mock.patch.object(self.node_settings.__class__, '_fetch_folder_name', return_value='fake_folder'):
            super().test_settings_detail_noncontrib_public_can_view

    def test_settings_detail_GET_enabled(self):
        with mock.patch.object(self.node_settings.__class__, '_fetch_folder_name', return_value='fake_folder'):
            super().test_settings_detail_GET_enabled


class NodeUnmanageableAddonTestSuiteMixin(NodeAddonTestSuiteMixin):
    addon_type = 'UNMANAGEABLE'


class TestNodeInvalidAddon(NodeAddonTestSuiteMixin, ApiAddonTestCase):
    addon_type = 'INVALID'
    short_name = 'fake'


# UNMANAGEABLE

class TestNodeOsfStorageAddon(
        NodeUnmanageableAddonTestSuiteMixin,
        ApiAddonTestCase):
    short_name = 'osfstorage'


class TestNodeTwoFactorAddon(
        NodeUnmanageableAddonTestSuiteMixin,
        ApiAddonTestCase):
    short_name = 'twofactor'


class TestNodeWikiAddon(NodeUnmanageableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'wiki'


# OAUTH

class TestNodeBitbucketAddon(NodeOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'bitbucket'
    AccountFactory = BitbucketAccountFactory
    NodeSettingsFactory = BitbucketNodeSettingsFactory

    def _settings_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'repo': 'mock',
            'user': 'abc',
            'owner': self.node
        }


class TestNodeDataverseAddon(NodeOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'dataverse'
    AccountFactory = DataverseAccountFactory
    NodeSettingsFactory = DataverseNodeSettingsFactory

    def _settings_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            '_dataset_id': '1234567890',
            'owner': self.node
        }


class TestNodeGitHubAddon(NodeOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'github'
    AccountFactory = GitHubAccountFactory
    NodeSettingsFactory = GitHubNodeSettingsFactory

    def _settings_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'repo': 'mock',
            'user': 'abc',
            'owner': self.node
        }

    @mock.patch('addons.github.models.GitHubClient')
    def test_folder_list_GET_expected_behavior(self, mock_client):
        mock_repo = Repository.from_json(
            dumps(
                {
                    'name': 'test',
                    'id': '12345',
                    'archive_url': 'https://api.github.com/repos/{user}/mock-repo/{{archive_format}}{{/ref}}',
                    'assignees_url': 'https://api.github.com/repos/{user}/mock-repo/assignees{{/user}}',
                    'blobs_url': 'https://api.github.com/repos/{user}/mock-repo/git/blobs{{/sha}}',
                    'branches_url': 'https://api.github.com/repos/{user}/mock-repo/branches{{/bra.format('
                                    'user=user)nch}}',
                    'clone_url': 'https://github.com/{user}/mock-repo.git',
                    'collaborators_url': 'https://api.github.com/repos/{user}/mock-repo/collaborators{{/collaborator}}',
                    'comments_url': 'https://api.github.com/repos/{user}/mock-repo/comments{{/number}}',
                    'commits_url': 'https://api.github.com/repos/{user}/mock-repo/commits{{/sha}}',
                    'compare_url': 'https://api.github.com/repos/{user}/mock-repo/compare/{{base}}...{{head}}',
                    'contents_url': 'https://api.github.com/repos/{user}/mock-repo/contents/{{+path}}',
                    'contributors_url': 'https://api.github.com/repos/{user}/mock-repo/contributors',
                    'created_at': '2013-06-30T18:29:18Z',
                    'default_branch': 'dev',
                    'description': 'Simple, Pythonic, text processing--Sentiment analysis, part-of-speech tagging, '
                                   'noun phrase extraction, translation, and more.',
                    'downloads_url': 'https://api.github.com/repos/{user}/mock-repo/downloads',
                    'events_url': 'https://api.github.com/repos/{user}/mock-repo/events',
                    'fork': False,
                    'forks': 89,
                    'forks_count': 89,
                    'forks_url': 'https://api.github.com/repos/{user}/mock-repo/forks',
                    'full_name': '{user}/mock-repo',
                    'git_commits_url': 'https://api.github.com/repos/{user}/mock-repo/git/commits{{/sha}}',
                    'git_refs_url': 'https://api.github.com/repos/{user}/mock-repo/git/refs{{/sha}}',
                    'git_tags_url': 'https://api.github.com/repos/{user}/mock-repo/git/tags{{/sha}}',
                    'git_url': 'git://github.com/{user}/mock-repo.git',
                    'has_downloads': True,
                    'has_issues': True,
                    'has_wiki': True,
                    'homepage': 'https://mock-repo.readthedocs.org/',
                    'hooks_url': 'https://api.github.com/repos/{user}/mock-repo/hooks',
                    'html_url': 'https://github.com/{user}/mock-repo',
                    'issue_comment_url': 'https://api.github.com/repos/{user}/mock-repo/issues/comments/{{number}}',
                    'issue_events_url': 'https://api.github.com/repos/{user}/mock-repo/issues/events{{/number}}',
                    'issues_url': 'https://api.github.com/repos/{user}/mock-repo/issues{{/number}}',
                    'keys_url': 'https://api.github.com/repos/{user}/mock-repo/keys{{/key_id}}',
                    'labels_url': 'https://api.github.com/repos/{user}/mock-repo/labels{{/name}}',
                    'language': 'Python',
                    'languages_url': 'https://api.github.com/repos/{user}/mock-repo/languages',
                    'master_branch': 'dev',
                    'merges_url': 'https://api.github.com/repos/{user}/mock-repo/merges',
                    'milestones_url': 'https://api.github.com/repos/{user}/mock-repo/milestones{{/number}}',
                    'mirror_url': None,
                    'network_count': 89,
                    'notifications_url': 'https://api.github.com/repos/{user}/mock-repo/notifications{{?since,all,'
                                         'participating}}',
                    'open_issues': 2,
                    'open_issues_count': 2,
                    'owner': {
                        'avatar_url': 'https://gravatar.com/avatar/c74f9cfd7776305a82ede0b765d65402?d=https%3A%2F'
                                      '%2Fidenticons.github.com%2F3959fe3bcd263a12c28ae86a66ec75ef.png&r=x',
                        'events_url': 'https://api.github.com/users/{user}/events{{/privacy}}',
                        'followers_url': 'https://api.github.com/users/{user}/followers',
                        'following_url': 'https://api.github.com/users/{user}/following{{/other_user}}',
                        'gists_url': 'https://api.github.com/users/{user}/gists{{/gist_id}}',
                        'gravatar_id': 'c74f9cfd7776305a82ede0b765d65402',
                        'html_url': 'https://github.com/{user}',
                        'id': 2379650,
                        'login': '{user}',
                        'organizations_url': 'https://api.github.com/users/{user}/orgs',
                        'received_events_url': 'https://api.github.com/users/{user}/received_events',
                        'repos_url': 'https://api.github.com/users/{user}/repos',
                        'site_admin': False,
                        'starred_url': 'https://api.github.com/users/{user}/starred{{/owner}}{{/repo}}',
                        'subscriptions_url': 'https://api.github.com/users/{user}/subscriptions',
                        'type': 'User',
                        'url': 'https://api.github.com/users/{user}'
                    },
                    'private': '{private}',
                    'pulls_url': 'https://api.github.com/repos/{user}/mock-repo/pulls{{/number}}',
                    'pushed_at': '2013-12-30T16:05:54Z',
                    'releases_url': 'https://api.github.com/repos/{user}/mock-repo/releases{{/id}}',
                    'size': 8717,
                    'ssh_url': 'git@github.com:{user}/mock-repo.git',
                    'stargazers_count': 1469,
                    'stargazers_url': 'https://api.github.com/repos/{user}/mock-repo/stargazers',
                    'statuses_url': 'https://api.github.com/repos/{user}/mock-repo/statuses/{{sha}}',
                    'subscribers_count': 86,
                    'subscribers_url': 'https://api.github.com/repos/{user}/mock-repo/subscribers',
                    'subscription_url': 'https://api.github.com/repos/{user}/mock-repo/subscription',
                    'svn_url': 'https://github.com/{user}/mock-repo',
                    'tags_url': 'https://api.github.com/repos/{user}/mock-repo/tags',
                    'teams_url': 'https://api.github.com/repos/{user}/mock-repo/teams',
                    'trees_url': 'https://api.github.com/repos/{user}/mock-repo/git/trees{{/sha}}',
                    'updated_at': '2014-01-12T21:23:50Z',
                    'url': 'https://api.github.com/repos/{user}/mock-repo',
                    'watchers': 1469,
                    'watchers_count': 1469,
                    # NOTE: permissions are only available if authorized on the repo
                    'permissions': {'push': True},
                    'deployments_url': 'https://api.github.com/repos',
                    'archived': {},
                    'has_pages': False,
                    'has_projects': False,
                }
            ),
            GitHubSession()
        )

        mock_connection = mock.MagicMock()
        mock_client.return_value = mock_connection
        mock_connection.repos = mock.MagicMock(return_value=[mock_repo])
        mock_connection.my_orgs_repos = mock.MagicMock(return_value=[mock_repo])

        res = self.app.get(
            self.folder_url,
            auth=self.user.auth)

        addon_data = res.json['data'][0]['attributes']
        assert addon_data['kind'] in ('folder', 'repo')
        assert addon_data['name'] == self._mock_folder_result['name']
        assert addon_data['path'] == self._mock_folder_result['path']
        assert addon_data['folder_id'] == self._mock_folder_result['id']

    @property
    def _mock_folder_result(self):
        return {'path': '{user}/test',
                'kind': 'repo',
                'name': 'test',
                'provider': 'github',
                'id': '12345'}


class TestNodeMendeleyAddon(
        NodeOAuthCitationAddonTestSuiteMixin,
        ApiAddonTestCase):
    short_name = 'mendeley'
    AccountFactory = MendeleyAccountFactory
    NodeSettingsFactory = MendeleyNodeSettingsFactory

    @mock.patch('addons.mendeley.models.Mendeley._get_folders')
    def test_folder_list_GET_expected_behavior(self, mock_folders):
        mock_folder = mendeley.models.folders.Folder(json={
            'created': '2017-10-14T21:17:14.000Z',
            'id': 'fasdkljla-2341-4592-10po-fds0920dks0ds',
            'modified': '2017-10-14T21:18:00.000Z',
            'name': 'Test Mendeley Folder'
        }, session='session')

        mock_folders.return_value = [mock_folder]

        res = self.app.get(
            self.folder_url,
            auth=self.user.auth)

        addon_data = res.json['data'][0]['attributes']
        assert addon_data['kind'] == 'folder'
        assert addon_data['name'] == 'Test Mendeley Folder'
        assert addon_data['path'] == '/'
        assert addon_data['folder_id'] == 'fasdkljla-2341-4592-10po-fds0920dks0ds'

class TestNodeZoteroAddon(
        NodeOAuthCitationAddonTestSuiteMixin,
        ApiAddonTestCase):
    short_name = 'zotero'
    AccountFactory = ZoteroAccountFactory
    NodeSettingsFactory = ZoteroNodeSettingsFactory

    @mock.patch('addons.zotero.models.Zotero._fetch_libraries')
    def test_folder_list_GET_expected_behavior(self, mock_libraries):
        ## Testing top level - GET library behavior
        mock_library = {
            'data': {
                'description': '',
                'url': '',
                'libraryReading': 'members',
                'version': 1,
                'owner': 2533095,
                'fileEditing': 'members',
                'libraryEditing': 'members',
                'type': 'Private',
                'id': 18497322,
                'name': 'Group Library I'
            },
            'version': 1,
            'meta': {
                'lastModified': '2017-10-19T22:20:41Z',
                'numItems': 20,
                'created': '2017-10-19T22:20:41Z'
            },
            'id': 18497322
        }

        mock_libraries.return_value = [mock_library, 1]

        res = self.app.get(
            self.folder_url,
            auth=self.user.auth)

        addon_data = res.json['data'][0]['attributes']
        assert addon_data['kind'] == self._mock_folder_result['kind']
        assert addon_data['name'] == 'My Library'
        assert addon_data['path'] == 'personal'
        assert addon_data['folder_id'] == 'personal'

        addon_data = res.json['data'][1]['attributes']
        assert addon_data['kind'] == self._mock_folder_result['kind']
        assert addon_data['name'] == self._mock_folder_result['name']
        assert addon_data['path'] == self._mock_folder_result['path']
        assert addon_data['folder_id'] == self._mock_folder_result['id']

    @property
    def _mock_folder_result(self):
        return {'path': '18497322',
                'kind': 'library',
                'name': 'Group Library I',
                'provider': 'zotero',
                'id': '18497322'}

    @mock.patch('addons.zotero.models.Zotero._get_folders')
    def test_sub_folder_list_GET_expected_behavior(self, mock_folders):
        ## Testing second level - GET folder behavior
        mock_folder = {
            'library': {
                'type': 'group',
                'id': 18497322,
                'name': 'Group Library I'
            },
            'version': 14,
            'meta': {
                'numCollections': 0,
                'numItems': 1
            },
            'key': 'V63S7EUJ',
            'data': {
                'version': 14,
                'name': 'Test Folder',
                'key': 'FSCFSLREF',
                'parentCollection': 'False'
            }
        }

        mock_folders.return_value = [mock_folder]

        res = self.app.get(
            self.folder_url + '?id=18497322&path=18497322',
            auth=self.user.auth)

        addon_data = res.json['data'][0]['attributes']
        assert addon_data['kind'] == 'folder'
        assert addon_data['name'] == 'Test Folder'
        assert addon_data['path'] == '18497322'
        assert addon_data['folder_id'] == 'FSCFSLREF'

# CONFIGURABLE


class TestNodeFigshareAddon(
        NodeConfigurableAddonTestSuiteMixin,
        ApiAddonTestCase):
    short_name = 'figshare'
    AccountFactory = FigshareAccountFactory
    NodeSettingsFactory = FigshareNodeSettingsFactory

    def _settings_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'folder': '1234567890',
            'owner': self.node
        }

    @property
    def _mock_folder_result(self):
        return {
            'name': 'A Fileset',
            'path': 'fileset',
            'id': '1234567890',
            'kind': 'folder',
            'addon': 'figshare',
        }

    @mock.patch('addons.figshare.client.FigshareClient.get_folders')
    def test_folder_list_GET_expected_behavior(self, mock_folders):
        mock_folders.return_value = [self._mock_folder_result]
        super().test_folder_list_GET_expected_behavior()

    @mock.patch('addons.figshare.client.FigshareClient.get_linked_folder_info')
    def test_settings_detail_PUT_all_sets_settings(self, mock_info):
        mock_info.return_value = self._mock_folder_result
        super().test_settings_detail_PUT_all_sets_settings


class TestNodeBoxAddon(NodeConfigurableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'box'
    AccountFactory = BoxAccountFactory
    NodeSettingsFactory = BoxNodeSettingsFactory

    @property
    def _mock_folder_result(self):
        return {
            'name': '/ (Full Box)',
            'path': '/',
            'id': '0'
        }

    def test_settings_detail_PUT_all_sets_settings(self):
        with mock.patch('addons.box.models.Client.folder') as folder_mock:
            folder_mock.return_value.get.return_value = {
                'id': self._mock_folder_info['folder_id'],
                'name': 'FAKEFOLDERNAME',
                'path_collection': {'entries': {}}
            }
            with mock.patch('addons.box.models.Provider.refresh_oauth_key'):
                super().test_settings_detail_PUT_all_sets_settings()


class TestNodeDropboxAddon(
        NodeConfigurableAddonTestSuiteMixin,
        ApiAddonTestCase):
    short_name = 'dropbox'
    AccountFactory = DropboxAccountFactory
    NodeSettingsFactory = DropboxNodeSettingsFactory

    def _settings_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'folder': '1234567890',
            'owner': self.node
        }

    @property
    def _mock_folder_result(self):
        return {
            'name': '/ (Full Dropbox)',
            'path': '/',
            'id': '/'
        }


class TestNodeOwnCloudAddon(
        NodeConfigurableAddonTestSuiteMixin,
        ApiAddonTestCase):
    short_name = 'owncloud'
    AccountFactory = OwnCloudAccountFactory
    NodeSettingsFactory = OwnCloudNodeSettingsFactory

    def _settings_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'folder': '1234567890',
            'owner': self.node
        }

    @property
    def _mock_folder_result(self):
        return {
            'name': '/ (Full ownCloud)',
            'path': '/',
            'id': '/'
        }


class TestNodeS3Addon(NodeConfigurableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 's3'
    AccountFactory = S3AccountFactory
    NodeSettingsFactory = S3NodeSettingsFactory

    def _settings_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'owner': self.node
        }

    @property
    def _mock_folder_result(self):
        return {
            'name': 'a.bucket',
            'path': '/',
            'id': 'a.bucket:/'
        }

    @mock.patch('addons.s3.models.get_bucket_names')
    def test_folder_list_GET_expected_behavior(self, mock_names):
        mock_names.return_value = ['a.bucket']
        super().test_folder_list_GET_expected_behavior()

    @mock.patch('addons.s3.models.bucket_exists')
    @mock.patch('addons.s3.models.get_bucket_location_or_error')
    def test_settings_detail_PUT_all_sets_settings(
            self, mock_location, mock_exists):
        mock_exists.return_value = True
        mock_location.return_value = ''
        super().test_settings_detail_PUT_all_sets_settings()


class TestNodeGoogleDriveAddon(
        NodeConfigurableAddonTestSuiteMixin,
        ApiAddonTestCase):
    short_name = 'googledrive'
    AccountFactory = GoogleDriveAccountFactory
    NodeSettingsFactory = GoogleDriveNodeSettingsFactory

    def _settings_kwargs(self, node, user_settings):
        return {
            'folder_id': '1234567890',
            'folder_path': '/1234567890'
        }

    @property
    def _mock_folder_info(self):
        return {
            'folder_id': '0987654321',
            'folder_path': '/'
        }

    @property
    def _mock_folder_result(self):
        return {
            'name': '/ (Full Google Drive)',
            'path': '/',
            'id': 'FAKEROOTID'
        }

    @mock.patch('addons.googledrive.client.GoogleDriveClient.about')
    def test_folder_list_GET_expected_behavior(self, mock_about):
        mock_about.return_value = {'rootFolderId': 'FAKEROOTID'}
        with mock.patch.object(self.node_settings.__class__, 'fetch_access_token', return_value='asdfghjkl'):
            super().test_folder_list_GET_expected_behavior()

    def test_settings_detail_PUT_PATCH_only_folder_id_raises_error(self):
        self.node_settings.clear_settings()
        self.node_settings.save()
        data = {
            'data': {
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'folder_id': self._mock_folder_info['folder_id']
                }
            }
        }
        res_put = self.app.put_json_api(
            self.setting_detail_url, data,
            auth=self.user.auth, expect_errors=True
        )
        res_patch = self.app.patch_json_api(
            self.setting_detail_url, data,
            auth=self.user.auth, expect_errors=True
        )

        assert res_put.status_code == res_patch.status_code == 400
        assert (f'Must specify both folder_id and folder_path for {self.short_name}' ==
                res_put.json['errors'][0]['detail'] == res_patch.json['errors'][0]['detail'])

    def test_settings_detail_PUT_PATCH_only_folder_path_raises_error(self):
        self.node_settings.clear_settings()
        self.node_settings.save()
        data = {
            'data': {
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'folder_path': self._mock_folder_info['folder_path']
                }
            }
        }
        res_put = self.app.put_json_api(
            self.setting_detail_url, data,
            auth=self.user.auth, expect_errors=True
        )
        res_patch = self.app.patch_json_api(
            self.setting_detail_url, data,
            auth=self.user.auth, expect_errors=True
        )

        assert res_put.status_code == res_patch.status_code == 400
        assert (f'Must specify both folder_id and folder_path for {self.short_name}' ==
                res_put.json['errors'][0]['detail'] == res_patch.json['errors'][0]['detail'])

    def test_settings_detail_incomplete_PUT_raises_error(self):
        self.node_settings.deauthorize(auth=self.auth)
        self.node_settings.save()
        data = {
            'data': {
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'external_account_id': self.account_id,
                    'folder_id': self._mock_folder_info['folder_id']
                }
            }
        }
        res = self.app.put_json_api(
            self.setting_detail_url, data,
            auth=self.user.auth, expect_errors=True)

        assert res.status_code == 400
        assert f'Must specify both folder_id and folder_path for {self.short_name}' == res.json['errors'][0]['detail']


class TestNodeForwardAddon(
        NodeUnmanageableAddonTestSuiteMixin,
        ApiAddonTestCase):
    short_name = 'forward'

    @property
    def _mock_folder_info(self):
        return {
            'url': 'http://google.com',
            'label': 'Gewgle'
        }

    def setUp(self):
        super().setUp()
        self.addon_type = 'OAUTH'
        self.node_settings = self.node.get_or_add_addon(
            self.short_name, auth=self.auth)
        self.node_settings.url = 'http://google.com'
        self.node_settings.save()

    # Overrides

    def test_folder_list_GET_raises_error_admin_not_authorizer(self):
        self.should_expect_errors()
        admin_user = AuthUserFactory()
        self.node.add_contributor(
            admin_user, permissions=ADMIN,
            auth=self.auth)
        res = self.app.get(
            self.folder_url,
            auth=admin_user.auth,
            expect_errors=True)
        assert res.status_code == 501

    def test_folder_list_GET_raises_error_writecontrib_not_authorizer(self):
        write_user = AuthUserFactory()
        self.node.add_contributor(
            write_user,
            permissions=WRITE,
            auth=self.auth)
        res = self.app.get(
            self.folder_url,
            auth=write_user.auth,
            expect_errors=True)
        assert res.status_code == 501

    def test_settings_detail_GET_enabled(self):
        res = self.app.get(
            self.setting_detail_url,
            auth=self.user.auth)

        addon_data = res.json['data']['attributes']
        assert self.node_settings.url == addon_data['url']
        assert self.node_settings.label == addon_data['label']

    def test_settings_detail_POST_enables(self):
        self.node.delete_addon(self.short_name, auth=self.auth)
        res = self.app.post_json_api(
            self.setting_detail_url,
            {'data': {
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {}
            }},
            auth=self.user.auth)

        addon_data = res.json['data']['attributes']
        assert addon_data['url'] is None
        assert addon_data['label'] is None

        self.node.reload()
        assert self.node.logs.latest().action != 'forward_url_changed'

    def test_settings_detail_noncontrib_public_can_view(self):
        self.node.set_privacy('public', auth=self.auth)
        noncontrib = AuthUserFactory()
        res = self.app.get(
            self.setting_detail_url,
            auth=noncontrib.auth)

        assert res.status_code == 200
        addon_data = res.json['data']['attributes']
        assert self.node_settings.url == addon_data['url']
        assert self.node_settings.label == addon_data['label']

    def test_settings_list_GET_enabled(self):
        res = self.app.get(
            self.setting_list_url,
            auth=self.user.auth)

        addon_data = self.get_response_for_addon(res)
        assert self.node_settings.url == addon_data['url']
        assert self.node_settings.label == addon_data['label']

    def test_settings_list_noncontrib_public_can_view(self):
        self.node.set_privacy('public', auth=self.auth)
        noncontrib = AuthUserFactory()
        res = self.app.get(
            self.setting_list_url,
            auth=noncontrib.auth)
        addon_data = self.get_response_for_addon(res)

        assert self.node_settings.url == addon_data['url']
        assert self.node_settings.label == addon_data['label']

    def test_settings_detail_PATCH_to_add_folder_without_auth_conflict(self):
        # This test doesn't apply forward, as it does not use ExternalAccounts.
        # Overridden because it's required by the superclass.
        pass

    def test_settings_detail_PATCH_to_enable_and_add_external_account_id(self):
        # This test doesn't apply forward, as it does not use ExternalAccounts.
        # Overridden because it's required by the superclass.
        pass

    def test_settings_detail_PATCH_to_remove_external_account_id(self):
        # This test doesn't apply forward, as it does not use ExternalAccounts.
        # Overridden because it's required by the superclass.
        pass

    def test_settings_detail_PUT_all_sets_settings(self):
        self.node_settings.reset()
        self.node_settings.save()
        data = {
            'data': {
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {}
            }
        }
        data['data']['attributes'].update(self._mock_folder_info)
        res = self.app.put_json_api(self.setting_detail_url,
                                    data, auth=self.user.auth)
        addon_data = res.json['data']['attributes']
        assert addon_data['url'] == self._mock_folder_info['url']
        assert addon_data['label'] == self._mock_folder_info['label']

        self.node.reload()
        assert self.node.logs.latest().action == 'forward_url_changed'

    def test_settings_detail_PUT_none_and_enabled_clears_settings(self):
        res = self.app.put_json_api(
            self.setting_detail_url,
            {'data': {
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'url': '',
                    'label': ''
                }
            }}, auth=self.user.auth)
        addon_data = res.json['data']['attributes']
        assert not addon_data['url']
        assert not addon_data['label']

        assert self.node.logs.latest().action != 'forward_url_changed'

    def test_settings_detail_PUT_only_label_and_enabled_clears_settings(self):
        res = self.app.put_json_api(
            self.setting_detail_url,
            {'data': {
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'url': '',
                    'label': 'A Link'
                }
            }},
            auth=self.user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Cannot set label without url'

    def test_settings_detail_PUT_only_url_sets_settings(self):
        self.node_settings.reset()
        self.node_settings.save()
        data = {
            'data': {
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'url': self._mock_folder_info['url']
                }
            }
        }
        res = self.app.put_json_api(
            self.setting_detail_url,
            data, auth=self.user.auth)
        addon_data = res.json['data']['attributes']
        assert addon_data['url'] == self._mock_folder_info['url']
        assert not addon_data['label']

        self.node.reload()
        assert self.node.logs.latest().action == 'forward_url_changed'

    def test_settings_detail_PUT_none_and_disabled_deauthorizes(self):
        # This test doesn't apply forward, as it does not use ExternalAccounts.
        # Overridden because it's required by the superclass.
        pass
