import logging
from urllib import request
import time

from boaapi.boa_client import BoaClient, BoaException, BOA_API_ENDPOINT
from boaapi.status import CompilerStatus, ExecutionStatus

from addons.boa import settings as boa_settings
from addons.osfstorage.models import OsfStorageFile
from api.base.utils import waterbutler_api_url_for
from framework.celery_tasks import app as celery_app
from osf.models import OSFUser
from osf.utils.fields import ensure_str, ensure_bytes
from website import settings as osf_settings

logger = logging.getLogger(__name__)


@celery_app.task()
def submit_to_boa(file_guid, user_guid, target_data_set):

    user = OSFUser.objects.get(guids___id=user_guid)
    cookie_value = user.get_or_create_cookie().decode()
    logger.info(f'Downloading Boa query file {file_guid} ...')
    boa_file = OsfStorageFile.objects.get(guids___id=file_guid)
    file_download_wb_url = boa_file.generate_waterbutler_url()
    logger.info(f'File download link (default domain): {file_download_wb_url}')
    # TODO: do we need to do this replacement for server env? Or is this local only?
    file_download_wb_internal_url = file_download_wb_url.replace(osf_settings.WATERBUTLER_URL, osf_settings.WATERBUTLER_INTERNAL_URL)
    logger.info(f'File download link (internal domain): {file_download_wb_internal_url}')
    submit_request = request.Request(file_download_wb_internal_url)
    submit_request.add_header('Cookie', f'{osf_settings.COOKIE_NAME}={cookie_value}')
    boa_query = ensure_str(request.urlopen(submit_request).read())
    logger.info(f'Boa query downloaded:\n{boa_query}')

    # TODO: get user settings from DB
    user_settings = boa_settings.user_settings

    client = BoaClient(endpoint=BOA_API_ENDPOINT)
    try:
        client.login(user_settings['username'], user_settings['password'])
    except BoaException:
        logger.error('Login failed')
        client.close()
        # TODO: end error email
        return
    logger.info('Login successful')
    try:
        data_set = client.get_dataset(target_data_set)
    except BoaException:
        logger.error(f'Invalid data set: {target_data_set}!')
        client.close()
        # TODO: end error email
        return

    job = client.query(boa_query, data_set)
    logger.info('Query submitted')
    # TODO: turn this into async
    while job.is_running():
        job.refresh()
        logger.warning(f'Job {str(job.id)} still running, waiting 10s...')
        time.sleep(10)
    if job.compiler_status is CompilerStatus.ERROR:
        job_output = f'Job {str(job.id)} failed with compile error'
        logger.error(job_output)
        client.close()
        # TODO: end error email
        return
    elif job.compiler_status is ExecutionStatus.ERROR:
        job_output = f'Job {str(job.id)} failed with execution error'
        logger.error(job_output)
        client.close()
        # TODO: end error email
        return
    else:
        job_output = job.output()
        logger.info(f'Job {str(job.id)} finished with output:\n{job_output}')

    try:
        logger.info(f'Uploading job {str(job.id)} output to OSF ...')
        parent_folder = boa_file.parent
        logger.info(f'Output file parent: {parent_folder.path}')
        output_file_name = boa_file.name.replace('.boa', '_results.txt')
        logger.info(f'Output file name: {output_file_name}')
        base_url = None
        if hasattr(parent_folder.target, 'osfstorage_region'):
            base_url = parent_folder.target.osfstorage_region.waterbutler_url
        # TODO: similar to download, do we need to do this replacement for server env? Or is this local only?
        file_upload_wb_url = waterbutler_api_url_for(parent_folder.target._id, parent_folder.provider, parent_folder.path, base_url=base_url)
        logger.info(f'File upload link (domain): {file_upload_wb_url}')
        file_upload_wb_internal_url = file_upload_wb_url.replace(osf_settings.WATERBUTLER_URL, osf_settings.WATERBUTLER_INTERNAL_URL)
        logger.info(f'File upload link (internal domain): {file_upload_wb_internal_url}')
        submit_request = request.Request(f'{file_upload_wb_internal_url}?kind=file&name={output_file_name}')
        submit_request.method = 'PUT'
        submit_request.data = ensure_bytes(job_output)
        submit_request.add_header('Cookie', f'{osf_settings.COOKIE_NAME}={cookie_value}')
        request.urlopen(submit_request)
    except Exception:
        logger.error('Upload error!')
        client.close()
        client.close()
        # TODO: end error email
        return

    logger.info('Job done!')
    client.close()
    # TODO: end success email
    return
