import logging
from urllib import request
import time

from boaapi.boa_client import BoaClient, BoaException
from boaapi.status import CompilerStatus, ExecutionStatus

from addons.boa import settings as boa_settings
from framework.celery_tasks import app as celery_app
from osf.models import OSFUser
from osf.utils.fields import ensure_str, ensure_bytes
from website import settings as osf_settings

logger = logging.getLogger(__name__)


@celery_app.task()
def submit_to_boa(host, username, password, user_guid, query_dataset,
                  query_file_name, query_download_url, output_upload_url, ):
    """
    Note:
        * All the parameters must be verified by the caller.
        * Both the download and upload URL must be WB URL.
        * TODO: should we add ``node_guid`` to be included in emails to users.
    """

    user = OSFUser.objects.get(guids___id=user_guid)
    cookie_value = user.get_or_create_cookie().decode()

    logger.info(f'Downloading Boa query file {query_file_name} from {query_download_url} ...')
    download_request = request.Request(query_download_url)
    download_request.add_header('Cookie', f'{osf_settings.COOKIE_NAME}={cookie_value}')
    try:
        boa_query = ensure_str(request.urlopen(download_request).read())
    except Exception:
        logger.error(f'Failed to download Boa query!')
        # TODO: handle exception and send error email
        return
    logger.info('Boa query successfully downloaded.')
    logger.debug(f'Boa query:\n{boa_query}')

    client = BoaClient(endpoint=host)
    try:
        client.login(username, password)
    except BoaException:
        logger.error(f'Boa login failed for user {username} on {host}')
        client.close()
        # TODO: handle exception and send error email
        return
    logger.info(f'Boa login completed for user {username} on {host}')

    try:
        dataset = client.get_dataset(query_dataset)
    except BoaException:
        logger.error(f'Failed to retrieve/verify the target Boa dataset: {query_dataset}!')
        client.close()
        # TODO: handle exception and send error email
        return

    try:
        boa_job = client.query(boa_query, dataset)
    except BoaException:
        logger.error(f'Failed to submit the query to Boa API!')
        client.close()
        # TODO: handle exception and send error email
        return
    logger.info(f'Query submitted with job {str(boa_job.id)}. Waiting for job to finish ...')
    # TODO: turn this in to async sleep to avoid blocking celery
    # TODO: if async sleep still blocks our celery queue, spawn a new task
    while boa_job.is_running():
        boa_job.refresh()
        logger.warning(f'Boa job {str(boa_job.id)} still running, waiting 10s ...')
        time.sleep(10)
    if boa_job.compiler_status is CompilerStatus.ERROR:
        logger.error(f'Boa job {str(boa_job.id)} failed with compile error')
        client.close()
        # TODO: handle exception and send error email
        return
    elif boa_job.compiler_status is ExecutionStatus.ERROR:
        logger.error(f'Boa job {str(boa_job.id)} failed with execution error')
        client.close()
        # TODO: handle exception and send error email
        return
    else:
        boa_job_output = boa_job.output()
        client.close()
        logger.info(f'Boa job {str(boa_job.id)} successfully finished.')
        logger.info(f'Boa job {str(boa_job.id)} output:\n{boa_job_output}')

    output_file_name = query_file_name.replace('.boa', boa_settings.OUTPUT_FILE_SUFFIX)
    logger.info(f'Uploading Boa query output to {output_upload_url} with name {output_file_name} ...')

    try:
        upload_request = request.Request(f'{output_upload_url}&name={output_file_name}')
        upload_request.method = 'PUT'
        upload_request.data = ensure_bytes(boa_job_output)
        upload_request.add_header('Cookie', f'{osf_settings.COOKIE_NAME}={cookie_value}')
        request.urlopen(upload_request)
    except Exception:
        logger.error('Failed to upload file to OSF Storage')
        # TODO: handle exception and send error email
        return

    logger.info(f'Successfully uploaded {output_file_name} to OSF Storage')
    # TODO: wrap up the task and send success email
    return
