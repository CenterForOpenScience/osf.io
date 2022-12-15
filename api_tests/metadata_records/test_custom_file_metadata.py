import pytest

from api_tests.utils import create_test_file
from .test_custom_item_metadata import TestCustomItemMetadataRecordDetail as ParentTestClass


# the view at /v2/custom_file_metadata_records/ is almost identical to
# the view at /v2/custom_item_metadata_records/ with additional fields,
# so let's reuse test logic!
class TestCustomFileMetadataRecordDetail(ParentTestClass):
    APIV2_PATH = 'custom_file_metadata_records/'
    APIV2_RESOURCE_TYPE = 'custom-file-metadata-record'

    @pytest.fixture(scope='class')
    def public_preprint_file_osfguid(self, public_preprint):
        return public_preprint.primary_file.get_guid(create=True)

    @pytest.fixture(scope='class')
    def private_preprint_file_osfguid(self, private_preprint):
        return private_preprint.primary_file.get_guid(create=True)

    @pytest.fixture(scope='class')
    def public_project_file_osfguid(self, public_project, user_admin):
        public_file = create_test_file(public_project, user_admin, filename='public_file')
        return public_file.get_guid(create=True)

    @pytest.fixture(scope='class')
    def private_project_file_osfguid(self, private_project, user_admin):
        private_file = create_test_file(private_project, user_admin, filename='private_file')
        return private_file.get_guid(create=True)

    @pytest.fixture(scope='class')
    def public_registration_file_osfguid(self, public_registration, user_admin):
        public_reg_file = create_test_file(public_registration, user_admin, filename='public_reg_file')
        return public_reg_file.get_guid(create=True)

    @pytest.fixture(scope='class')
    def private_registration_file_osfguid(self, private_registration, user_admin):
        private_reg_file = create_test_file(private_registration, user_admin, filename='private_reg_file')
        return private_reg_file.get_guid(create=True)

    # override super().public_osfguid
    @pytest.fixture
    def public_osfguid(self, item_type, public_preprint_file_osfguid, public_project_file_osfguid, public_registration_file_osfguid):
        if item_type == 'preprint':
            return public_preprint_file_osfguid
        if item_type == 'project':
            return public_project_file_osfguid
        if item_type == 'registration':
            return public_registration_file_osfguid
        raise NotImplementedError

    # override super().public_osfguid
    @pytest.fixture
    def private_osfguid(self, item_type, private_preprint_file_osfguid, private_project_file_osfguid, private_registration_file_osfguid):
        if item_type == 'preprint':
            return private_preprint_file_osfguid
        if item_type == 'project':
            return private_project_file_osfguid
        if item_type == 'registration':
            return private_registration_file_osfguid
        raise NotImplementedError
