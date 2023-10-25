import asynctest
import mock
import pytest

from addons.boa.boa_error_code import BoaErrorCode
from addons.boa.tasks import submit_to_boa
from addons.boa.tests.async_mock import AsyncMock
from osf_tests.factories import AuthUserFactory, ProjectFactory
from tests.base import OsfTestCase


class TestBoaErrorCode(OsfTestCase):

    def test_boa_error_code(self):
        assert BoaErrorCode.NO_ERROR == -1
        assert BoaErrorCode.UNKNOWN == 0
        assert BoaErrorCode.AUTHN_ERROR == 1
        assert BoaErrorCode.QUERY_ERROR == 2
        assert BoaErrorCode.UPLOAD_ERROR_CONFLICT == 3
        assert BoaErrorCode.UPLOAD_ERROR_OTHER == 4
        assert BoaErrorCode.OUTPUT_ERROR == 5


class TestSubmitToBoa(OsfTestCase):

    def setUp(self):
        super(TestSubmitToBoa, self).setUp()
        self.host = 'http://locahost:9999/boa/?q=boa/api'
        self.username = 'fake-boa-username'
        self.password = 'fake-boa-password'
        self.user_guid = AuthUserFactory()._id
        self.project_guid = ProjectFactory()._id
        self.query_dataset = '2023 Oct / Fake Boa Dataset (small)'
        self.query_file_name = 'fake_boa_script.boa'
        self.file_full_path = '/fake_boa_folder/fake_boa_script.boa'
        self.query_download_url = f'http://localhost:7777/v1/resources/{self.project_guid}/providers/osfstorage/1a2b3c4d'
        self.output_upload_url = f'http://localhost:7777/v1/resources/{self.project_guid}/providers/osfstorage/?kind=file'

    def tearDown(self):
        super(TestSubmitToBoa, self).tearDown()

    def test_submit_to_boa_async_called(self):
        with mock.patch(
                'addons.boa.tasks.submit_to_boa_async',
                new_callable=AsyncMock,
                return_value=BoaErrorCode.NO_ERROR
        ) as mock_submit_to_boa_async:
            return_value = submit_to_boa(
                self.host,
                self.username,
                self.password,
                self.user_guid,
                self.project_guid,
                self.query_dataset,
                self.query_file_name,
                self.file_full_path,
                self.query_download_url,
                self.output_upload_url
            )
            mock_submit_to_boa_async.assert_called()
            assert return_value == BoaErrorCode.NO_ERROR


@pytest.mark.django_db
class TestSubmitToBoaAsync(OsfTestCase, asynctest.TestCase):
    pass
