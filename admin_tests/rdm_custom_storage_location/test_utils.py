import pytest
from mock import patch, MagicMock
from nose import tools as nt

from admin.rdm_custom_storage_location.utils import get_providers, add_node_settings_to_projects
from osf_tests.factories import InstitutionFactory, ProjectFactory, RegionFactory, bulkmount_waterbutler_settings, addon_waterbutler_settings, AuthUserFactory


@pytest.mark.feature_202210
@pytest.mark.django_db
class TestUtils:
    def test_get_providers(self):
        provider_list = get_providers()
        assert provider_list
        provider_list_short_name = [p.short_name for p in provider_list]
        nt.assert_in('s3', provider_list_short_name, 's3')
        nt.assert_in('box', provider_list_short_name, 'box')
        nt.assert_in('dropboxbusiness', provider_list_short_name, 'dropboxbusiness')
        nt.assert_in('googledrive', provider_list_short_name, 'googledrive')
        nt.assert_in('nextcloud', provider_list_short_name, 'nextcloud')
        nt.assert_in('nextcloudinstitutions', provider_list_short_name, 'nextcloudinstitutions')
        nt.assert_in('osfstorage', provider_list_short_name, 'osfstorage')
        nt.assert_in('onedrivebusiness', provider_list_short_name, 'onedrivebusiness')
        nt.assert_in('swift', provider_list_short_name, 'swift')
        nt.assert_in('ociinstitutions', provider_list_short_name, 'ociinstitutions')
        nt.assert_in('owncloud', provider_list_short_name, 'owncloud')
        nt.assert_in('s3compat', provider_list_short_name, 's3compat')
        nt.assert_in('s3compatinstitutions', provider_list_short_name, 's3compatinstitutions')

        provider_list = get_providers(available_list=[])
        nt.assert_equal(len(provider_list), 0)

        available_list = ['s3', 's3compat']
        provider_list = get_providers(available_list=available_list)
        provider_list_short_name = [p.short_name for p in provider_list]
        nt.assert_list_equal(provider_list_short_name, available_list)

    def test_add_node_settings_to_projects_bulk_mount_storage(self):
        user = AuthUserFactory()
        project = ProjectFactory(creator=user)
        region = RegionFactory(waterbutler_settings=bulkmount_waterbutler_settings)
        institution = InstitutionFactory.create(_id=region.guid)
        institution.nodes.set([project])
        user.affiliated_institutions.add(institution)

        mock_dropboxbusiness_post_save = MagicMock()
        mock_onedrivebusiness_post_save = MagicMock()
        mock_node_post_save = MagicMock()
        with patch('admin.rdm_custom_storage_location.utils.dropboxbusiness_post_save', mock_dropboxbusiness_post_save):
            with patch('admin.rdm_custom_storage_location.utils.onedrivebusiness_post_save', mock_onedrivebusiness_post_save):
                with patch('admin.rdm_custom_storage_location.utils.node_post_save', mock_node_post_save):
                    add_node_settings_to_projects(institution, 'osfstorage')
                    mock_dropboxbusiness_post_save.assert_not_called()
                    mock_onedrivebusiness_post_save.assert_not_called()
                    mock_node_post_save.assert_not_called()

    def test_add_node_settings_to_projects_dropboxbusiness(self):
        user = AuthUserFactory()
        project = ProjectFactory(creator=user)
        region = RegionFactory(waterbutler_settings=addon_waterbutler_settings)
        institution = InstitutionFactory.create(_id=region.guid)
        institution.nodes.set([project])
        user.affiliated_institutions.add(institution)

        mock_dropboxbusiness_post_save = MagicMock()
        mock_onedrivebusiness_post_save = MagicMock()
        mock_node_post_save = MagicMock()
        with patch('admin.rdm_custom_storage_location.utils.dropboxbusiness_post_save', mock_dropboxbusiness_post_save):
            with patch('admin.rdm_custom_storage_location.utils.onedrivebusiness_post_save', mock_onedrivebusiness_post_save):
                with patch('admin.rdm_custom_storage_location.utils.node_post_save', mock_node_post_save):
                    add_node_settings_to_projects(institution, 'dropboxbusiness')
                    mock_dropboxbusiness_post_save.assert_called()
                    mock_onedrivebusiness_post_save.assert_not_called()
                    mock_node_post_save.assert_not_called()

    def test_add_node_settings_to_projects_onedrivebusiness(self):
        user = AuthUserFactory()
        project = ProjectFactory(creator=user)
        project.add_addon('onedrivebusiness', None)
        project.save()
        region = RegionFactory(waterbutler_settings=addon_waterbutler_settings)
        institution = InstitutionFactory.create(_id=region.guid)
        institution.nodes.set([project])
        user.affiliated_institutions.add(institution)

        mock_dropboxbusiness_post_save = MagicMock()
        mock_onedrivebusiness_post_save = MagicMock()
        mock_node_post_save = MagicMock()
        with patch('admin.rdm_custom_storage_location.utils.dropboxbusiness_post_save', mock_dropboxbusiness_post_save):
            with patch('admin.rdm_custom_storage_location.utils.onedrivebusiness_post_save', mock_onedrivebusiness_post_save):
                with patch('admin.rdm_custom_storage_location.utils.node_post_save', mock_node_post_save):
                    add_node_settings_to_projects(institution, 'onedrivebusiness')
                    mock_dropboxbusiness_post_save.assert_not_called()
                    mock_onedrivebusiness_post_save.assert_called()
                    mock_node_post_save.assert_not_called()

    def test_add_node_settings_to_projects_other_add_on_storage(self):
        user = AuthUserFactory()
        project = ProjectFactory(creator=user)
        region = RegionFactory(waterbutler_settings=addon_waterbutler_settings)
        institution = InstitutionFactory.create(_id=region.guid)
        institution.nodes.set([project])
        user.affiliated_institutions.add(institution)

        mock_dropboxbusiness_post_save = MagicMock()
        mock_onedrivebusiness_post_save = MagicMock()
        mock_node_post_save = MagicMock()
        with patch('admin.rdm_custom_storage_location.utils.dropboxbusiness_post_save', mock_dropboxbusiness_post_save):
            with patch('admin.rdm_custom_storage_location.utils.onedrivebusiness_post_save', mock_onedrivebusiness_post_save):
                with patch('admin.rdm_custom_storage_location.utils.node_post_save', mock_node_post_save):
                    add_node_settings_to_projects(institution, 'nextcloudinstitutions')
                    mock_dropboxbusiness_post_save.assert_not_called()
                    mock_onedrivebusiness_post_save.assert_not_called()
                    mock_node_post_save.assert_called()
