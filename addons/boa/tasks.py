import asyncio
from http.client import HTTPException
import logging
import time

from asgiref.sync import async_to_sync, sync_to_async
from boaapi.boa_client import BoaClient, BoaException
from boaapi.status import CompilerStatus, ExecutionStatus
from urllib import request
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

from addons.boa import settings as boa_settings
from addons.boa.boa_error_code import BoaErrorCode
from framework import sentry
from framework.celery_tasks import app as celery_app
from osf.models import OSFUser, NotificationType
from osf.utils.fields import ensure_str, ensure_bytes
from website import settings as osf_settings

logger = logging.getLogger(__name__)


@celery_app.task(name='addons.boa.tasks.submit_to_boa')
def submit_to_boa(host, username, password, user_guid, project_guid,
                  query_dataset, query_file_name, file_size, file_full_path,
                  query_download_url, output_upload_url):
    """
    Download Boa query file, submit it to Boa API, wait for Boa to finish the job
    and upload result output to OSF. Send success / failure emails notifications.

    A few Notes:
        * All the parameters must be verified by the caller.
        * Both the ``query_download_url`` and ``output_upload_url`` must be WB URL for two reasons:
            * It generates fewer requests between OSF and WB;
            * It has authentication passed via the headers securely.
        * Running asyncio in celery is tricky. Refer to the discussion below for details:
            * https://stackoverflow.com/questions/39815771/how-to-combine-celery-with-asyncio
    """
    return async_to_sync(submit_to_boa_async)(host, username, password, user_guid, project_guid,
                                              query_dataset, query_file_name, file_size, file_full_path,
                                              query_download_url, output_upload_url)


async def submit_to_boa_async(host, username, password, user_guid, project_guid,
                              query_dataset, query_file_name, file_size, file_full_path,
                              query_download_url, output_upload_url):
    """
    Download Boa query file, submit it to Boa API, wait for Boa to finish the job
    and upload result output to OSF. Send success / failure emails notifications.

    A couple of notes:
        * This is the async function that must be wrapped with ``async_to_sync`` by the caller
        * See notes in ``submit_to_boa()`` for details.
    """

    logger.debug('>>>>>>>> Task begins')
    user = await sync_to_async(OSFUser.objects.get)(guids___id=user_guid)
    cookie_value = (await sync_to_async(user.get_or_create_cookie)()).decode()
    project_url = f'{osf_settings.DOMAIN}{project_guid}/'
    output_file_name = query_file_name.replace('.boa', boa_settings.OUTPUT_FILE_SUFFIX)

    if file_size > boa_settings.MAX_SUBMISSION_SIZE:
        message = f'Boa query file too large to submit: user=[{user_guid}], project=[{project_guid}], ' \
                  f'file_name=[{query_file_name}], file_size=[{file_size}], ' \
                  f'full_path=[{file_full_path}], url=[{query_download_url}] ...'
        await sync_to_async(handle_boa_error)(message, BoaErrorCode.FILE_TOO_LARGE_ERROR,
                                              user.username, user.fullname, project_url, file_full_path,
                                              query_file_name=query_file_name, file_size=file_size)
        return BoaErrorCode.FILE_TOO_LARGE_ERROR

    logger.debug(f'Downloading Boa query file: user=[{user_guid}], project=[{project_guid}], '
                 f'file_name=[{query_file_name}], full_path=[{file_full_path}], url=[{query_download_url}] ...')
    download_request = request.Request(query_download_url)
    download_request.add_header('Cookie', f'{osf_settings.COOKIE_NAME}={cookie_value}')
    try:
        boa_query = ensure_str(request.urlopen(download_request).read())
    except (ValueError, HTTPError, URLError, HTTPException):
        message = f'Failed to download Boa query file: user=[{user_guid}], project=[{project_guid}], ' \
                  f'file_name=[{query_file_name}], full_path=[{file_full_path}], url=[{query_download_url}] ...'
        await sync_to_async(handle_boa_error)(message, BoaErrorCode.UNKNOWN, user.username, user.fullname,
                                              project_url, file_full_path, query_file_name=query_file_name)
        return BoaErrorCode.UNKNOWN
    logger.info('Boa query successfully downloaded.')
    logger.debug(f'Boa query:\n########\n{boa_query}\n########')

    logger.debug('Boa client opened.')
    client = BoaClient(endpoint=host)
    logger.debug(f'Checking Boa credentials: boa_username=[{username}], boa_host=[{host}] ...')
    try:
        client.login(username, password)
    except BoaException:
        # Don't call `client.close()`, since it will fail with `BoaException` if `client.login()` fails
        message = f'Boa login failed: boa_username=[{username}], boa_host=[{host}]!'
        await sync_to_async(handle_boa_error)(message, BoaErrorCode.AUTHN_ERROR, user.username, user.fullname,
                                              project_url, file_full_path, query_file_name=query_file_name)
        return BoaErrorCode.AUTHN_ERROR
    logger.info('Boa login completed.')

    logger.debug(f'Retrieving Boa dataset: dataset=[{query_dataset}] ...')
    try:
        dataset = client.get_dataset(query_dataset)
    except BoaException:
        client.close()
        message = f'Failed to retrieve or verify the target Boa dataset: dataset=[{query_dataset}]!'
        await sync_to_async(handle_boa_error)(message, BoaErrorCode.UNKNOWN, user.username, user.fullname,
                                              project_url, file_full_path, query_file_name=query_file_name)
        return BoaErrorCode.UNKNOWN
    logger.info('Boa dataset retrieved.')

    logger.debug(f'Submitting the query to Boa API: boa_host=[{host}], dataset=[{query_dataset}] ...')
    try:
        boa_job = client.query(boa_query, dataset)
        start_time = time.time()
    except BoaException:
        client.close()
        message = f'Failed to submit the query to Boa API: : boa_host=[{host}], dataset=[{query_dataset}]!'
        await sync_to_async(handle_boa_error)(message, BoaErrorCode.UNKNOWN, user.username, user.fullname,
                                              project_url, file_full_path, query_file_name=query_file_name)
        return BoaErrorCode.UNKNOWN
    logger.info('Query successfully submitted.')
    logger.debug(f'Waiting for job to finish: job_id=[{str(boa_job.id)}] ...')
    while boa_job.is_running():
        if time.time() - start_time > boa_settings.MAX_JOB_WAITING_TIME:
            client.close()
            message = f'Boa job did not complete in time: job_id=[{str(boa_job.id)}]!'
            await sync_to_async(handle_boa_error)(message, BoaErrorCode.JOB_TIME_OUT_ERROR,
                                                  user.username, user.fullname, project_url, file_full_path,
                                                  query_file_name=query_file_name, job_id=boa_job.id)
            return BoaErrorCode.JOB_TIME_OUT_ERROR
        logger.debug(f'Boa job still running, waiting 10s: job_id=[{str(boa_job.id)}] ...')
        boa_job.refresh()
        await asyncio.sleep(boa_settings.REFRESH_JOB_INTERVAL)
    if boa_job.compiler_status is CompilerStatus.ERROR:
        client.close()
        message = f'Boa job failed with compile error: job_id=[{str(boa_job.id)}]!'
        await sync_to_async(handle_boa_error)(message, BoaErrorCode.QUERY_ERROR, user.username,
                                              user.fullname, project_url, file_full_path,
                                              query_file_name=query_file_name, job_id=boa_job.id)
        return BoaErrorCode.QUERY_ERROR
    elif boa_job.exec_status is ExecutionStatus.ERROR:
        client.close()
        message = f'Boa job failed with execution error: job_id=[{str(boa_job.id)}]!'
        await sync_to_async(handle_boa_error)(message, BoaErrorCode.QUERY_ERROR, user.username,
                                              user.fullname, project_url, file_full_path,
                                              query_file_name=query_file_name, job_id=boa_job.id)
        return BoaErrorCode.QUERY_ERROR
    else:
        try:
            boa_job_output = boa_job.output()
        except BoaException:
            client.close()
            message = f'Boa job output is not available: job_id=[{str(boa_job.id)}]!'
            await sync_to_async(handle_boa_error)(message, BoaErrorCode.OUTPUT_ERROR, user.username,
                                                  user.fullname, project_url, file_full_path,
                                                  query_file_name=query_file_name, job_id=boa_job.id)
            return BoaErrorCode.OUTPUT_ERROR
        logger.info('Boa job finished.')
        logger.debug(f'Boa job output: job_id=[{str(boa_job.id)}]\n########\n{boa_job_output}\n########')
        client.close()
        logger.debug('Boa client closed.')

    logger.debug(f'Uploading Boa query output to OSF: name=[{output_file_name}], upload_url=[{output_upload_url}] ...')
    try:
        output_query_param = urlencode({'name': output_file_name})
        upload_request = request.Request(f'{output_upload_url}&{output_query_param}')
        upload_request.method = 'PUT'
        upload_request.data = ensure_bytes(boa_job_output)
        upload_request.add_header('Cookie', f'{osf_settings.COOKIE_NAME}={cookie_value}')
        request.urlopen(upload_request)
    except (ValueError, HTTPError, URLError, HTTPException) as e:
        message = f'Failed to upload query output file to OSF: ' \
                  f'name=[{output_file_name}], user=[{user_guid}], url=[{output_upload_url}]!'
        error_code = BoaErrorCode.UPLOAD_ERROR_OTHER
        if isinstance(e, HTTPError):
            message += f', http_error=[{e.code}: {e.reason}]'
            if e.code == 409:
                error_code = BoaErrorCode.UPLOAD_ERROR_CONFLICT
        await sync_to_async(handle_boa_error)(message, error_code, user.username, user.fullname, project_url,
                                              file_full_path, query_file_name=query_file_name,
                                              output_file_name=output_file_name, job_id=boa_job.id)
        return error_code

    logger.info('Successfully uploaded query output to OSF.')
    logger.debug('Task ends <<<<<<<<')
    NotificationType.Type.ADDONS_BOA_JOB_COMPLETE.instance.emit(
        user=user,
        event_context={
            'fullname': user.fullname,
            'query_file_name': query_file_name,
            'query_file_full_path': file_full_path,
            'output_file_name': output_file_name,
            'job_id': boa_job.id,
            'project_url': project_url,
            'boa_job_list_url': boa_settings.BOA_JOB_LIST_URL,
            'boa_support_email': boa_settings.BOA_SUPPORT_EMAIL,
            'osf_support_email': osf_settings.OSF_SUPPORT_EMAIL,
        }
    )
    return BoaErrorCode.NO_ERROR


def handle_boa_error(message, code, username, fullname, project_url, query_file_full_path,
                     query_file_name=None, file_size=None, output_file_name=None, job_id=None):
    """Handle Boa and WB API errors and send emails.
    """
    logger.error(message)
    try:
        sentry.log_message(message, skip_session=True)
    except Exception:
        pass
    NotificationType.Type.ADDONS_BOA_JOB_FAILURE.instance.emit(
        destination_address=username,
        event_context={
            'user_fullname': fullname,
            'code': code,
            'query_file_name': query_file_name,
            'file_size': file_size,
            'message': message,
            'max_file_size': boa_settings.MAX_SUBMISSION_SIZE,
            'query_file_full_path': query_file_full_path,
            'output_file_name': output_file_name,
            'job_id': job_id,
            'max_job_wait_hours': boa_settings.MAX_JOB_WAITING_TIME / 3600,
            'project_url': project_url,
            'boa_job_list_url': boa_settings.BOA_JOB_LIST_URL,
            'boa_support_email': boa_settings.BOA_SUPPORT_EMAIL,
            'osf_support_email': osf_settings.OSF_SUPPORT_EMAIL,

        }
    )
    return code
