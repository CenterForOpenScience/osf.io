import pytest
from django.apps import apps
from addons.s3.utils import update_folder_names, reverse_update_folder_names

@pytest.mark.django_db
class TestUpdateFolderNamesMigration:

    def test_update_folder_names_migration(self):
        from addons.s3.models import NodeSettings
        from addons.s3.tests.factories import S3NodeSettingsFactory
        # Create sample folder names and IDs
        S3NodeSettingsFactory(folder_name='Folder 1 (Location 1)', folder_id='folder1')
        S3NodeSettingsFactory(folder_name='Folder 2', folder_id='folder2')
        S3NodeSettingsFactory(folder_name='Folder 3 (Location 3)', folder_id='folder3')

        update_folder_names()

        # Verify updated folder names and IDs
        updated_folder_names_ids = NodeSettings.objects.values_list('folder_name', 'folder_id')
        expected_updated_folder_names_ids = {
            ('Folder 1:/ (Location 1)', 'folder1:/'),
            ('Folder 2:/', 'folder2:/'),
            ('Folder 3:/ (Location 3)', 'folder3:/'),
        }
        assert set(updated_folder_names_ids) == expected_updated_folder_names_ids

        # Reverse the migration
        reverse_update_folder_names()

        # Verify the folder names and IDs after the reverse migration
        reverted_folder_names_ids = NodeSettings.objects.values_list('folder_name', 'folder_id')
        expected_reverted_folder_names_ids = {
            ('Folder 1 (Location 1)', 'folder1'),
            ('Folder 2', 'folder2'),
            ('Folder 3 (Location 3)', 'folder3'),
        }
        assert set(reverted_folder_names_ids) == expected_reverted_folder_names_ids
