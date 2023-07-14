import pytest
from nose import tools as nt

from admin.rdm_custom_storage_location.utils import get_providers


@pytest.mark.feature_202210
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
