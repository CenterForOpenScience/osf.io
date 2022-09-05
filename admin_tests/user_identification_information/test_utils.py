import pytest
from nose import tools as nt

from addons.dataverse.tests.factories import DataverseNodeSettingsFactory, DataverseAccountFactory
from addons.github.tests.factories import GitHubNodeSettingsFactory, GitHubAccountFactory
from addons.googledrive.tests.factories import GoogleDriveNodeSettingsFactory, GoogleDriveAccountFactory
# from addons.dropbox.tests.factories import DropboxNodeSettingsFactory, DropboxAccountFactory
from addons.mendeley.tests.factories import MendeleyNodeSettingsFactory, MendeleyAccountFactory
from addons.owncloud.tests.factories import OwnCloudNodeSettingsFactory, OwnCloudAccountFactory
from addons.s3.tests.factories import (S3NodeSettingsFactory, S3AccountFactory, )
from addons.weko.tests.factories import WEKONodeSettingsFactory, WEKOAccountFactory
from admin.user_identification_information import utils
from admin.user_identification_information import views
from osf_tests.factories import (
    AuthUserFactory,
)
from tests.base import AdminTestCase

pytestmark = pytest.mark.django_db


class TestUtils(AdminTestCase):

    def setUp(self):
        self.user = AuthUserFactory(fullname='Test User1')
        self.user2 = AuthUserFactory(fullname='Broken Matt Hardy')
        self.user3 = AuthUserFactory(fullname='Test User3')
        self.user.is_superuser = False
        self.user2.is_superuser = True
        self.user3.is_staff = True

    def test_custom_size_abbreviation_abbr_is_B(self):
        size = 9
        abbr = 'GB'
        results = views.custom_size_abbreviation(size, abbr)

        nt.assert_equal(results[0], 9)
        nt.assert_equal(results[1], 'GB')

    def test_custom_size_abbreviation(self):
        size = 90000
        abbr = 'B'
        results = views.custom_size_abbreviation(size, abbr)

        nt.assert_equal(results[0], 90)
        nt.assert_equal(results[1], 'KB')

    def test_get_list_extend_storage_s3(self):

        self.user.add_addon('s3')
        self.user_settings = self.user.get_addon('s3')
        self.external_account = S3AccountFactory(provider_name='Amazon S3')
        self.user_settings.owner.external_accounts.add(self.external_account)
        self.user_settings.owner.save()
        self.S3Node_settings = S3NodeSettingsFactory(user_settings=self.user_settings)
        self.S3Node_settings.save()

        self.user.add_addon('s3')
        self.user_settings = self.user.get_addon('s3')
        self.external_account = S3AccountFactory(provider_name='Amazon S3')
        self.user_settings.owner.external_accounts.add(self.external_account)
        self.user_settings.owner.save()
        self.S3Node_settings = S3NodeSettingsFactory(user_settings=self.user_settings)
        self.S3Node_settings.save()

        list_name = []
        results = utils.get_list_extend_storage()
        nt.assert_is_instance(results, dict)

        for k, v in results.items():
            list_name.append(v[0])
        nt.assert_in('/Amazon S3', list_name)

    def test_get_list_extend_storage_github(self):
        self.user.add_addon('github')
        self.user_settings = self.user.get_addon('github')
        self.external_account = GitHubAccountFactory(provider_name='Github name')
        self.user_settings.owner.external_accounts.add(self.external_account)
        self.user_settings.owner.save()
        self.GitHubNode_settings = GitHubNodeSettingsFactory(user_settings=self.user_settings)

        list_name = []
        results = utils.get_list_extend_storage()

        for k, v in results.items():
            list_name.append(v[0])
        nt.assert_in('/Github name', list_name)

    def test_get_list_extend_storage_googledrive(self):
        self.user.add_addon('googledrive')
        self.user_settings = self.user.get_addon('googledrive')
        self.external_account = GoogleDriveAccountFactory(provider_name='googledrive name')
        self.user_settings.owner.external_accounts.add(self.external_account)
        self.user_settings.owner.save()
        self.GoogleDriveNode_settings = GoogleDriveNodeSettingsFactory(user_settings=self.user_settings)

        list_name = []
        results = utils.get_list_extend_storage()

        for k, v in results.items():
            list_name.append(v[0])

        nt.assert_in('/googledrive name', list_name[0])

    def test_get_list_extend_storage_weko(self):
        self.user.add_addon('weko')
        self.user_settings = self.user.get_addon('weko')
        self.external_account = WEKOAccountFactory(provider_name='weko name')
        self.user_settings.owner.external_accounts.add(self.external_account)
        self.user_settings.owner.save()
        self.WEKONode_settings = WEKONodeSettingsFactory(user_settings=self.user_settings)

        list_name = []
        results = utils.get_list_extend_storage()

        for k, v in results.items():
            list_name.append(v[0])

        nt.assert_in('/weko name', list_name[0])

    def test_get_list_extend_storage_mendeley(self):
        self.user.add_addon('mendeley')
        self.user_settings = self.user.get_addon('mendeley')
        self.external_account = MendeleyAccountFactory(provider_name='mendeley name')
        self.user_settings.owner.external_accounts.add(self.external_account)
        self.user_settings.owner.save()
        self.MendeleyNode_settings = MendeleyNodeSettingsFactory(user_settings=self.user_settings)

        list_name = []
        results = utils.get_list_extend_storage()

        for k, v in results.items():
            list_name.append(v[0])

        nt.assert_in('/mendeley name', list_name[0])

    def test_get_list_extend_storage_owncloud(self):
        self.user.add_addon('owncloud')
        self.user_settings = self.user.get_addon('owncloud')
        self.external_account = OwnCloudAccountFactory(provider_name='owncloud name')
        self.user_settings.owner.external_accounts.add(self.external_account)
        self.user_settings.owner.save()
        self.OwnCloudNode_settings = OwnCloudNodeSettingsFactory(user_settings=self.user_settings)

        list_name = []
        results = utils.get_list_extend_storage()

        for k, v in results.items():
            list_name.append(v[0])

        nt.assert_in('/owncloud name', list_name[0])

    def test_get_list_extend_storage_dataverse(self):
        self.user.add_addon('dataverse')
        self.user_settings = self.user.get_addon('dataverse')
        self.external_account = DataverseAccountFactory(provider_name='dataverse name')
        self.user_settings.owner.external_accounts.add(self.external_account)
        self.user_settings.owner.save()
        self.DataverseNode_settings = DataverseNodeSettingsFactory(user_settings=self.user_settings)

        list_name = []
        results = utils.get_list_extend_storage()

        for k, v in results.items():
            list_name.append(v[0])

        nt.assert_in('/dataverse name', list_name[0])

    # def test_get_list_extend_storage_dropbox(self):
    #     self.user.add_addon('dropbox')
    #     self.user_settings = self.user.get_addon('dropbox')
    #     self.external_account = DropboxAccountFactory(provider_name='dropbox name')
    #     self.user_settings.owner.external_accounts.add(self.external_account)
    #     self.user_settings.owner.save()
    #     self.DropboxNode_settings = DropboxNodeSettingsFactory(user_settings=self.user_settings)
    #
    #     list_name = []
    #     results = utils.get_list_extend_storage()
    #
    #     for k, v in results.items():
    #         list_name.append(v[0])
    #
    #     nt.assert_in('/dropbox name', list_name[0])