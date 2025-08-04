from boaapi.boa_client import BoaException
from boaapi.status import CompilerStatus, ExecutionStatus
from http.client import HTTPMessage
from unittest import mock
import pytest
from unittest.mock import ANY, MagicMock
from urllib.error import HTTPError

from addons.boa import settings as boa_settings
from addons.boa.boa_error_code import BoaErrorCode
from addons.boa.tasks import submit_to_boa, submit_to_boa_async, handle_boa_error
from osf_tests.factories import AuthUserFactory, ProjectFactory
from tests.base import OsfTestCase
from website import settings as osf_settings
from website.mails import ADDONS_BOA_JOB_COMPLETE, ADDONS_BOA_JOB_FAILURE

DEFAULT_REFRESH_JOB_INTERVAL = boa_settings.REFRESH_JOB_INTERVAL
DEFAULT_MAX_JOB_WAITING_TIME = boa_settings.MAX_JOB_WAITING_TIME


class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


class TestBoaErrorHandling(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.error_message = 'fake-error-message'
        self.user_username = 'fake-user-username'
        self.user_fullname = 'fake-user-fullname'
        self.project_url = 'http://localhost:5000/1a2b3'
        self.query_file_name = 'fake_boa_script.boa'
        self.file_size = 255
        self.max_job_wait_hours = boa_settings.MAX_JOB_WAITING_TIME / 3600
        self.file_full_path = '/fake_boa_folder/fake_boa_script.boa'
        self.output_file_name = 'fake_boa_script_results.txt'
        self.job_id = '1a2b3c4d5e6f7g8'

    def tearDown(self):
        super().tearDown()

    def test_boa_error_code(self):
        assert BoaErrorCode.NO_ERROR == -1
        assert BoaErrorCode.UNKNOWN == 0
        assert BoaErrorCode.AUTHN_ERROR == 1
        assert BoaErrorCode.QUERY_ERROR == 2
        assert BoaErrorCode.UPLOAD_ERROR_CONFLICT == 3
        assert BoaErrorCode.UPLOAD_ERROR_OTHER == 4
        assert BoaErrorCode.OUTPUT_ERROR == 5
        assert BoaErrorCode.FILE_TOO_LARGE_ERROR == 6
        assert BoaErrorCode.JOB_TIME_OUT_ERROR == 7

    def test_handle_boa_error(self):
        with mock.patch('addons.boa.tasks.send_mail', return_value=None) as mock_send_mail, \
                mock.patch('addons.boa.tasks.sentry.log_message', return_value=None) as mock_sentry_log_message, \
                mock.patch('addons.boa.tasks.logger.error', return_value=None) as mock_logger_error:
            return_value = handle_boa_error(
                self.error_message,
                BoaErrorCode.UNKNOWN,
                self.user_username,
                self.user_fullname,
                self.project_url,
                self.file_full_path,
                query_file_name=self.query_file_name,
                file_size=self.file_size,
                output_file_name=self.output_file_name,
                job_id=self.job_id
            )
            mock_send_mail.assert_called_with(
                to_addr=self.user_username,
                mail=ADDONS_BOA_JOB_FAILURE,
                fullname=self.user_fullname,
                code=BoaErrorCode.UNKNOWN,
                message=self.error_message,
                query_file_name=self.query_file_name,
                file_size=self.file_size,
                max_file_size=boa_settings.MAX_SUBMISSION_SIZE,
                query_file_full_path=self.file_full_path,
                output_file_name=self.output_file_name,
                job_id=self.job_id,
                max_job_wait_hours=self.max_job_wait_hours,
                project_url=self.project_url,
                boa_job_list_url=boa_settings.BOA_JOB_LIST_URL,
                boa_support_email=boa_settings.BOA_SUPPORT_EMAIL,
                osf_support_email=osf_settings.OSF_SUPPORT_EMAIL,
            )
            mock_sentry_log_message.assert_called_with(self.error_message, skip_session=True)
            mock_logger_error.assert_called_with(self.error_message)
            assert return_value == BoaErrorCode.UNKNOWN


class TestSubmitToBoa(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.host = 'http://locahost:9999/boa/?q=boa/api'
        self.username = 'fake-boa-username'
        self.password = 'fake-boa-password'
        self.user_guid = AuthUserFactory()._id
        self.project_guid = ProjectFactory()._id
        self.query_dataset = '2023 Oct / Fake Boa Dataset (small)'
        self.query_file_name = 'fake_boa_script.boa'
        self.file_size = 255
        self.file_full_path = '/fake_boa_folder/fake_boa_script.boa'
        self.query_download_url = f'http://localhost:7777/v1/resources/{self.project_guid}/providers/osfstorage/1a2b3c4d'
        self.output_upload_url = f'http://localhost:7777/v1/resources/{self.project_guid}/providers/osfstorage/?kind=file'

    def tearDown(self):
        super().tearDown()

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
                self.file_size,
                self.file_full_path,
                self.query_download_url,
                self.output_upload_url
            )
            assert return_value == BoaErrorCode.NO_ERROR
            mock_submit_to_boa_async.assert_called()


@pytest.mark.django_db
@pytest.mark.asyncio
class TestSubmitToBoaAsync(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.host = 'http://locahost:9999/boa/?q=boa/api'
        self.username = 'fake-boa-username'
        self.password = 'fake-boa-password'
        self.user = AuthUserFactory()
        self.user_guid = self.user._id
        self.user_cookie = self.user.get_or_create_cookie()
        self.project_guid = ProjectFactory()._id
        self.project_url = f'{osf_settings.DOMAIN}{self.project_guid}/'
        self.query_dataset = '2023 Oct / Fake Boa Dataset (small)'
        self.query_file_name = 'fake_boa_script.boa'
        self.file_size = 255
        self.file_size_too_large = boa_settings.MAX_SUBMISSION_SIZE + 255
        self.output_file_name = 'fake_boa_script_results.txt'
        self.file_full_path = '/fake_boa_folder/fake_boa_script.boa'
        self.query_download_url = f'http://localhost:7777/v1/resources/{self.project_guid}/providers/osfstorage/1a2b3c4d'
        self.output_upload_url = f'http://localhost:7777/v1/resources/{self.project_guid}/providers/osfstorage/?kind=file'
        self.mock_resp = mock.Mock()
        self.mock_resp.read.return_value = 'fake-boa-query-string'
        self.mock_job = mock.Mock()
        self.mock_job.id = '1a2b3c4d5e6f7g8'
        self.mock_job.is_running.side_effect = [True, True, True, True, False]
        self.mock_job.refresh.return_value = None
        self.mock_job.compiler_status = CompilerStatus.FINISHED
        self.mock_job.exec_status = ExecutionStatus.FINISHED
        self.mock_job.output.return_value = 'fake-boa-output-string'
        boa_settings.REFRESH_JOB_INTERVAL = DEFAULT_REFRESH_JOB_INTERVAL
        boa_settings.MAX_JOB_WAITING_TIME = DEFAULT_MAX_JOB_WAITING_TIME

    def tearDown(self):
        super().tearDown()

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
                self.file_size,
                self.file_full_path,
                self.query_download_url,
                self.output_upload_url,
            )
            assert return_value == BoaErrorCode.NO_ERROR
            assert self.mock_job.is_running.call_count == 5
            assert self.mock_job.refresh.call_count == 4
            assert mock_async_sleep.call_count == 4
            mock_close.assert_called()
            mock_send_mail.assert_called_with(
                to_addr=self.user.username,
                mail=ADDONS_BOA_JOB_COMPLETE,
                fullname=self.user.fullname,
                query_file_name=self.query_file_name,
                query_file_full_path=self.file_full_path,
                output_file_name=self.output_file_name,
                job_id=self.mock_job.id,
                project_url=self.project_url,
                boa_job_list_url=boa_settings.BOA_JOB_LIST_URL,
                boa_support_email=boa_settings.BOA_SUPPORT_EMAIL,
                osf_support_email=osf_settings.OSF_SUPPORT_EMAIL,
            )
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
                self.file_size,
                self.file_full_path,
                self.query_download_url,
                self.output_upload_url,
            )
            assert return_value == BoaErrorCode.UNKNOWN
            mock_handle_boa_error.assert_called_with(
                ANY,
                BoaErrorCode.UNKNOWN,
                self.user.username,
                self.user.fullname,
                self.project_url,
                self.file_full_path,
                query_file_name=self.query_file_name,
            )

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
                self.file_size,
                self.file_full_path,
                self.query_download_url,
                self.output_upload_url,
            )
            assert return_value == BoaErrorCode.AUTHN_ERROR
            mock_login.assert_called_with(self.username, self.password)
            mock_close.assert_not_called()
            mock_handle_boa_error.assert_called_with(
                ANY,
                BoaErrorCode.AUTHN_ERROR,
                self.user.username,
                self.user.fullname,
                self.project_url,
                self.file_full_path,
                query_file_name=self.query_file_name,
            )

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
                self.file_size,
                self.file_full_path,
                self.query_download_url,
                self.output_upload_url,
            )
            assert return_value == BoaErrorCode.UNKNOWN
            mock_get_dataset.assert_called()
            mock_close.assert_called()
            mock_handle_boa_error.assert_called_with(
                ANY,
                BoaErrorCode.UNKNOWN,
                self.user.username,
                self.user.fullname,
                self.project_url,
                self.file_full_path,
                query_file_name=self.query_file_name,
            )

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
                self.file_size,
                self.file_full_path,
                self.query_download_url,
                self.output_upload_url,
            )
            assert return_value == BoaErrorCode.UNKNOWN
            mock_query.assert_called()
            mock_close.assert_called()
            mock_handle_boa_error.assert_called_with(
                ANY,
                BoaErrorCode.UNKNOWN,
                self.user.username,
                self.user.fullname,
                self.project_url,
                self.file_full_path,
                query_file_name=self.query_file_name,
            )

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
                self.file_size,
                self.file_full_path,
                self.query_download_url,
                self.output_upload_url,
            )
            assert return_value == BoaErrorCode.QUERY_ERROR
            mock_close.assert_called()
            mock_handle_boa_error.assert_called_with(
                ANY,
                BoaErrorCode.QUERY_ERROR,
                self.user.username,
                self.user.fullname,
                self.project_url,
                self.file_full_path,
                query_file_name=self.query_file_name,
                job_id=self.mock_job.id,
            )

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
                self.file_size,
                self.file_full_path,
                self.query_download_url,
                self.output_upload_url,
            )
            assert return_value == BoaErrorCode.QUERY_ERROR
            mock_close.assert_called()
            mock_handle_boa_error.assert_called_with(
                ANY,
                BoaErrorCode.QUERY_ERROR,
                self.user.username,
                self.user.fullname,
                self.project_url,
                self.file_full_path,
                query_file_name=self.query_file_name,
                job_id=self.mock_job.id,
            )

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
                self.file_size,
                self.file_full_path,
                self.query_download_url,
                self.output_upload_url,
            )
            assert return_value == BoaErrorCode.OUTPUT_ERROR
            self.mock_job.output.assert_called()
            mock_close.assert_called()
            mock_handle_boa_error.assert_called_with(
                ANY,
                BoaErrorCode.OUTPUT_ERROR,
                self.user.username,
                self.user.fullname,
                self.project_url,
                self.file_full_path,
                query_file_name=self.query_file_name,
                job_id=self.mock_job.id,
            )

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
                self.file_size,
                self.file_full_path,
                self.query_download_url,
                self.output_upload_url,
            )
            assert return_value == BoaErrorCode.UPLOAD_ERROR_CONFLICT
            mock_close.assert_called()
            mock_handle_boa_error.assert_called_with(
                ANY,
                BoaErrorCode.UPLOAD_ERROR_CONFLICT,
                self.user.username,
                self.user.fullname,
                self.project_url,
                self.file_full_path,
                query_file_name=self.query_file_name,
                output_file_name=self.output_file_name,
                job_id=self.mock_job.id,
            )

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
                self.file_size,
                self.file_full_path,
                self.query_download_url,
                self.output_upload_url,
            )
            assert return_value == BoaErrorCode.UPLOAD_ERROR_OTHER
            mock_close.assert_called()
            mock_handle_boa_error.assert_called_with(
                ANY,
                BoaErrorCode.UPLOAD_ERROR_OTHER,
                self.user.username,
                self.user.fullname,
                self.project_url,
                self.file_full_path,
                query_file_name=self.query_file_name,
                output_file_name=self.output_file_name,
                job_id=self.mock_job.id,
            )

    async def test_file_too_large_error(self):
        with mock.patch('osf.models.user.OSFUser.objects.get', return_value=self.user), \
                mock.patch('osf.models.user.OSFUser.get_or_create_cookie', return_value=self.user_cookie), \
                mock.patch('addons.boa.tasks.handle_boa_error', return_value=None) as mock_handle_boa_error:
            return_value = await submit_to_boa_async(
                self.host,
                self.username,
                self.password,
                self.user_guid,
                self.project_guid,
                self.query_dataset,
                self.query_file_name,
                self.file_size_too_large,
                self.file_full_path,
                self.query_download_url,
                self.output_upload_url,
            )
            assert return_value == BoaErrorCode.FILE_TOO_LARGE_ERROR
            mock_handle_boa_error.assert_called_with(
                ANY,
                BoaErrorCode.FILE_TOO_LARGE_ERROR,
                self.user.username,
                self.user.fullname,
                self.project_url,
                self.file_full_path,
                query_file_name=self.query_file_name,
                file_size=self.file_size_too_large,
            )

    async def test_job_timeout_error(self):
        boa_settings.REFRESH_JOB_INTERVAL = 1
        boa_settings.MAX_JOB_WAITING_TIME = 1
        with mock.patch('osf.models.user.OSFUser.objects.get', return_value=self.user), \
                mock.patch('osf.models.user.OSFUser.get_or_create_cookie', return_value=self.user_cookie), \
                mock.patch('urllib.request.urlopen', return_value=self.mock_resp), \
                mock.patch('boaapi.boa_client.BoaClient.login', return_value=None), \
                mock.patch('boaapi.boa_client.BoaClient.get_dataset', return_value=self.query_dataset), \
                mock.patch('boaapi.boa_client.BoaClient.query', return_value=self.mock_job), \
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
                self.file_size,
                self.file_full_path,
                self.query_download_url,
                self.output_upload_url,
            )
            assert return_value == BoaErrorCode.JOB_TIME_OUT_ERROR
            mock_close.assert_called()
            mock_handle_boa_error.assert_called_with(
                ANY,
                BoaErrorCode.JOB_TIME_OUT_ERROR,
                self.user.username,
                self.user.fullname,
                self.project_url,
                self.file_full_path,
                query_file_name=self.query_file_name,
                job_id=self.mock_job.id,
            )
