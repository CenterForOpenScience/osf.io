from asynctest import TestCase as AsyncTestCase
from boaapi.boa_client import BoaException
from boaapi.status import CompilerStatus, ExecutionStatus
from http.client import HTTPMessage
import mock
import pytest
from urllib.error import HTTPError

from addons.boa.boa_error_code import BoaErrorCode
from addons.boa.tasks import submit_to_boa, submit_to_boa_async
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
            assert return_value == BoaErrorCode.NO_ERROR
            mock_submit_to_boa_async.assert_called()


@pytest.mark.django_db
class TestSubmitToBoaAsync(OsfTestCase, AsyncTestCase):

    def setUp(self):
        super(TestSubmitToBoaAsync, self).setUp()
        self.host = 'http://locahost:9999/boa/?q=boa/api'
        self.username = 'fake-boa-username'
        self.password = 'fake-boa-password'
        self.user = AuthUserFactory()
        self.user_guid = self.user._id
        self.user_cookie = self.user.get_or_create_cookie()
        self.project_guid = ProjectFactory()._id
        self.query_dataset = '2023 Oct / Fake Boa Dataset (small)'
        self.query_file_name = 'fake_boa_script.boa'
        self.file_full_path = '/fake_boa_folder/fake_boa_script.boa'
        self.query_download_url = f'http://localhost:7777/v1/resources/{self.project_guid}/providers/osfstorage/1a2b3c4d'
        self.output_upload_url = f'http://localhost:7777/v1/resources/{self.project_guid}/providers/osfstorage/?kind=file'
        self.mock_resp = mock.Mock()
        self.mock_resp.read.return_value = 'fake-boa-query-string'
        self.mock_job = mock.Mock()
        self.mock_job.is_running.side_effect = [True, True, True, True, False]
        self.mock_job.refresh.return_value = None
        self.mock_job.compiler_status = CompilerStatus.FINISHED
        self.mock_job.exec_status = ExecutionStatus.FINISHED
        self.mock_job.output.return_value = 'fake-boa-output-string'

    def tearDown(self):
        super(TestSubmitToBoaAsync, self).tearDown()

    async def test_submit_success(self):
        with mock.patch('osf.models.user.OSFUser.objects.get', return_value=self.user), \
                mock.patch('osf.models.user.OSFUser.get_or_create_cookie', return_value=self.user_cookie), \
                mock.patch('urllib.request.urlopen', side_effect=[self.mock_resp, self.mock_resp]), \
                mock.patch('boaapi.boa_client.BoaClient.login', return_value=None), \
                mock.patch('boaapi.boa_client.BoaClient.get_dataset', return_value=self.query_dataset), \
                mock.patch('boaapi.boa_client.BoaClient.query', return_value=self.mock_job), \
                mock.patch('boaapi.boa_client.BoaClient.close', return_value=None) as mock_close, \
                mock.patch('asyncio.sleep', new_callable=AsyncMock, return_value=None) as mock_async_sleep, \
                mock.patch('addons.boa.tasks.send_mail', return_value=None) as mock_send_mail, \
                mock.patch('addons.boa.tasks.handle_boa_error', return_value=None) as mock_handle_boa_error:
            return_value = await submit_to_boa_async(
                self.host,
                self.username,
                self.password,
                self.user_guid,
                self.project_guid,
                self.query_dataset,
                self.query_file_name,
                self.file_full_path,
                self.query_download_url,
                self.output_upload_url,
            )
            assert return_value == BoaErrorCode.NO_ERROR
            assert mock_async_sleep.call_count == 4
            mock_close.assert_called()
            mock_send_mail.assert_called()
            mock_handle_boa_error.assert_not_called()

    async def test_download_error(self):
        http_404 = HTTPError(self.host, 404, 'Not Found', HTTPMessage(), None)
        with mock.patch('osf.models.user.OSFUser.objects.get', return_value=self.user), \
                mock.patch('osf.models.user.OSFUser.get_or_create_cookie', return_value=self.user_cookie), \
                mock.patch('urllib.request.urlopen', side_effect=http_404), \
                mock.patch('addons.boa.tasks.handle_boa_error', return_value=None) as mock_handle_boa_error:
            return_value = await submit_to_boa_async(
                self.host,
                self.username,
                self.password,
                self.user_guid,
                self.project_guid,
                self.query_dataset,
                self.query_file_name,
                self.file_full_path,
                self.query_download_url,
                self.output_upload_url,
            )
            assert return_value == BoaErrorCode.UNKNOWN
            mock_handle_boa_error.assert_called()

    async def test_login_error(self):
        with mock.patch('osf.models.user.OSFUser.objects.get', return_value=self.user), \
                mock.patch('osf.models.user.OSFUser.get_or_create_cookie', return_value=self.user_cookie), \
                mock.patch('urllib.request.urlopen', return_value=self.mock_resp), \
                mock.patch('boaapi.boa_client.BoaClient.login', side_effect=BoaException()) as mock_login, \
                mock.patch('boaapi.boa_client.BoaClient.close', return_value=None) as mock_close, \
                mock.patch('addons.boa.tasks.handle_boa_error', return_value=None) as mock_handle_boa_error:
            return_value = await submit_to_boa_async(
                self.host,
                self.username,
                self.password,
                self.user_guid,
                self.project_guid,
                self.query_dataset,
                self.query_file_name,
                self.file_full_path,
                self.query_download_url,
                self.output_upload_url,
            )
            mock_login.assert_called()
            assert return_value == BoaErrorCode.AUTHN_ERROR
            mock_close.assert_called()
            mock_handle_boa_error.assert_called()

    async def test_data_set_error(self):
        with mock.patch('osf.models.user.OSFUser.objects.get', return_value=self.user), \
                mock.patch('osf.models.user.OSFUser.get_or_create_cookie', return_value=self.user_cookie), \
                mock.patch('urllib.request.urlopen', return_value=self.mock_resp), \
                mock.patch('boaapi.boa_client.BoaClient.login', return_value=None), \
                mock.patch('boaapi.boa_client.BoaClient.get_dataset', side_effect=BoaException()) as mock_get_dataset, \
                mock.patch('boaapi.boa_client.BoaClient.close', return_value=None) as mock_close, \
                mock.patch('addons.boa.tasks.handle_boa_error', return_value=None) as mock_handle_boa_error:
            return_value = await submit_to_boa_async(
                self.host,
                self.username,
                self.password,
                self.user_guid,
                self.project_guid,
                self.query_dataset,
                self.query_file_name,
                self.file_full_path,
                self.query_download_url,
                self.output_upload_url,
            )
            mock_get_dataset.assert_called()
            assert return_value == BoaErrorCode.UNKNOWN
            mock_close.assert_called()
            mock_handle_boa_error.assert_called()

    async def test_submit_error(self):
        with mock.patch('osf.models.user.OSFUser.objects.get', return_value=self.user), \
                mock.patch('osf.models.user.OSFUser.get_or_create_cookie', return_value=self.user_cookie), \
                mock.patch('urllib.request.urlopen', return_value=self.mock_resp), \
                mock.patch('boaapi.boa_client.BoaClient.login', return_value=None), \
                mock.patch('boaapi.boa_client.BoaClient.get_dataset', return_value=self.query_dataset), \
                mock.patch('boaapi.boa_client.BoaClient.query', side_effect=BoaException()) as mock_query, \
                mock.patch('boaapi.boa_client.BoaClient.close', return_value=None) as mock_close, \
                mock.patch('addons.boa.tasks.handle_boa_error', return_value=None) as mock_handle_boa_error:
            return_value = await submit_to_boa_async(
                self.host,
                self.username,
                self.password,
                self.user_guid,
                self.project_guid,
                self.query_dataset,
                self.query_file_name,
                self.file_full_path,
                self.query_download_url,
                self.output_upload_url,
            )
            mock_query.assert_called()
            assert return_value == BoaErrorCode.UNKNOWN
            mock_close.assert_called()
            mock_handle_boa_error.assert_called()

    async def test_compile_error(self):
        self.mock_job.compiler_status = CompilerStatus.ERROR
        self.mock_job.exec_status = ExecutionStatus.WAITING
        with mock.patch('osf.models.user.OSFUser.objects.get', return_value=self.user), \
                mock.patch('osf.models.user.OSFUser.get_or_create_cookie', return_value=self.user_cookie), \
                mock.patch('urllib.request.urlopen', return_value=self.mock_resp), \
                mock.patch('boaapi.boa_client.BoaClient.login', return_value=None), \
                mock.patch('boaapi.boa_client.BoaClient.get_dataset', return_value=self.query_dataset), \
                mock.patch('boaapi.boa_client.BoaClient.query', return_value=self.mock_job), \
                mock.patch('boaapi.boa_client.BoaClient.close', return_value=None) as mock_close, \
                mock.patch('asyncio.sleep', new_callable=AsyncMock, return_value=None), \
                mock.patch('addons.boa.tasks.handle_boa_error', return_value=None) as mock_handle_boa_error:
            return_value = await submit_to_boa_async(
                self.host,
                self.username,
                self.password,
                self.user_guid,
                self.project_guid,
                self.query_dataset,
                self.query_file_name,
                self.file_full_path,
                self.query_download_url,
                self.output_upload_url,
            )
            assert return_value == BoaErrorCode.QUERY_ERROR
            mock_close.assert_called()
            mock_handle_boa_error.assert_called()

    async def test_execute_error(self):
        self.mock_job.compiler_status = CompilerStatus.FINISHED
        self.mock_job.exec_status = ExecutionStatus.ERROR
        with mock.patch('osf.models.user.OSFUser.objects.get', return_value=self.user), \
                mock.patch('osf.models.user.OSFUser.get_or_create_cookie', return_value=self.user_cookie), \
                mock.patch('urllib.request.urlopen', return_value=self.mock_resp), \
                mock.patch('boaapi.boa_client.BoaClient.login', return_value=None), \
                mock.patch('boaapi.boa_client.BoaClient.get_dataset', return_value=self.query_dataset), \
                mock.patch('boaapi.boa_client.BoaClient.query', return_value=self.mock_job), \
                mock.patch('boaapi.boa_client.BoaClient.close', return_value=None) as mock_close, \
                mock.patch('asyncio.sleep', new_callable=AsyncMock, return_value=None), \
                mock.patch('addons.boa.tasks.handle_boa_error', return_value=None) as mock_handle_boa_error:
            return_value = await submit_to_boa_async(
                self.host,
                self.username,
                self.password,
                self.user_guid,
                self.project_guid,
                self.query_dataset,
                self.query_file_name,
                self.file_full_path,
                self.query_download_url,
                self.output_upload_url,
            )
            assert return_value == BoaErrorCode.QUERY_ERROR
            mock_close.assert_called()
            mock_handle_boa_error.assert_called()

    async def test_output_error_(self):
        self.mock_job.output.side_effect = BoaException()
        with mock.patch('osf.models.user.OSFUser.objects.get', return_value=self.user), \
                mock.patch('osf.models.user.OSFUser.get_or_create_cookie', return_value=self.user_cookie), \
                mock.patch('urllib.request.urlopen', return_value=self.mock_resp), \
                mock.patch('boaapi.boa_client.BoaClient.login', return_value=None), \
                mock.patch('boaapi.boa_client.BoaClient.get_dataset', return_value=self.query_dataset), \
                mock.patch('boaapi.boa_client.BoaClient.query', return_value=self.mock_job), \
                mock.patch('boaapi.boa_client.BoaClient.close', return_value=None) as mock_close, \
                mock.patch('asyncio.sleep', new_callable=AsyncMock, return_value=None), \
                mock.patch('addons.boa.tasks.handle_boa_error', return_value=None) as mock_handle_boa_error:
            return_value = await submit_to_boa_async(
                self.host,
                self.username,
                self.password,
                self.user_guid,
                self.project_guid,
                self.query_dataset,
                self.query_file_name,
                self.file_full_path,
                self.query_download_url,
                self.output_upload_url,
            )
            self.mock_job.output.assert_called()
            assert return_value == BoaErrorCode.OUTPUT_ERROR
            mock_close.assert_called()
            mock_handle_boa_error.assert_called()

    async def test_upload_error_conflict(self):
        http_409 = HTTPError(self.host, 409, 'Conflict', HTTPMessage(), None)
        with mock.patch('osf.models.user.OSFUser.objects.get', return_value=self.user), \
                mock.patch('osf.models.user.OSFUser.get_or_create_cookie', return_value=self.user_cookie), \
                mock.patch('urllib.request.urlopen', side_effect=[self.mock_resp, http_409]), \
                mock.patch('boaapi.boa_client.BoaClient.login', return_value=None), \
                mock.patch('boaapi.boa_client.BoaClient.get_dataset', return_value=self.query_dataset), \
                mock.patch('boaapi.boa_client.BoaClient.query', return_value=self.mock_job), \
                mock.patch('boaapi.boa_client.BoaClient.close', return_value=None) as mock_close, \
                mock.patch('asyncio.sleep', new_callable=AsyncMock, return_value=None), \
                mock.patch('addons.boa.tasks.handle_boa_error', return_value=None) as mock_handle_boa_error:
            return_value = await submit_to_boa_async(
                self.host,
                self.username,
                self.password,
                self.user_guid,
                self.project_guid,
                self.query_dataset,
                self.query_file_name,
                self.file_full_path,
                self.query_download_url,
                self.output_upload_url,
            )
            assert return_value == BoaErrorCode.UPLOAD_ERROR_CONFLICT
            mock_close.assert_called()
            mock_handle_boa_error.assert_called()

    async def test_upload_error_other(self):
        http_503 = HTTPError(self.host, 503, 'Service Unavailable', HTTPMessage(), None)
        with mock.patch('osf.models.user.OSFUser.objects.get', return_value=self.user), \
                mock.patch('osf.models.user.OSFUser.get_or_create_cookie', return_value=self.user_cookie), \
                mock.patch('urllib.request.urlopen', side_effect=[self.mock_resp, http_503]), \
                mock.patch('boaapi.boa_client.BoaClient.login', return_value=None), \
                mock.patch('boaapi.boa_client.BoaClient.get_dataset', return_value=self.query_dataset), \
                mock.patch('boaapi.boa_client.BoaClient.query', return_value=self.mock_job), \
                mock.patch('boaapi.boa_client.BoaClient.close', return_value=None) as mock_close, \
                mock.patch('asyncio.sleep', new_callable=AsyncMock, return_value=None), \
                mock.patch('addons.boa.tasks.handle_boa_error', return_value=None) as mock_handle_boa_error:
            return_value = await submit_to_boa_async(
                self.host,
                self.username,
                self.password,
                self.user_guid,
                self.project_guid,
                self.query_dataset,
                self.query_file_name,
                self.file_full_path,
                self.query_download_url,
                self.output_upload_url,
            )
            assert return_value == BoaErrorCode.UPLOAD_ERROR_OTHER
            mock_close.assert_called()
            mock_handle_boa_error.assert_called()
