import json
import logging
import os
import shutil
import tempfile
from urllib.parse import unquote

from flask import request
import requests
from bs4 import BeautifulSoup

from framework.exceptions import HTTPError
from framework.celery_tasks import app as celery_app
from osf.models import OSFUser
from rest_framework import status as http_status
from website.project.decorators import (
    must_be_valid_project,
    must_have_addon,
    must_have_permission,
)
from website.util import api_url_for, waterbutler

from . import SHORT_NAME
from .settings import MAX_IMPORTABLE_DATASET_BYTES

logger = logging.getLogger(__name__)

@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
@must_have_permission('write')
def metadata_import_dataset(auth, provider, filepath, **kwargs):
    node = kwargs['node'] or kwargs['project']
    dataset_url = request.json.get('url', None)
    if not dataset_url:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    logger.info('Importing dataset from {} to {}'.format(dataset_url, filepath))
    task = import_dataset.delay(
        auth.user._id,
        node._id,
        dataset_url,
        provider,
        '/' + filepath,
    )
    urlparams = dict([(k, v) for k, v in kwargs.items() if k in ['nid', 'pid']] + [('task_id', task.task_id)])
    if 'nid' not in kwargs:
        urlparams['nid'] = '<no_node>'
    progress_api_url = api_url_for(
        'metadata_get_importing_dataset',
        **urlparams,
    )
    progress_api_url = progress_api_url.replace('/node/%3Cno_node%3E', '')
    return {
        'node_id': node._id,
        'task_id': task.task_id,
        'progress_api_url': progress_api_url,
    }

@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
@must_have_permission('write')
def metadata_get_importing_dataset(auth, task_id=None, **kwargs):
    result = celery_app.AsyncResult(task_id)
    error = None
    info = {}
    if result.failed():
        logger.info(f'Failed: {result.info}: {type(result.info)}')
        error = str(result.info)
    elif result.info is not None and auth.user._id != result.info['user']:
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)
    elif result.info is not None:
        info.update(result.info)
    return {
        'state': result.state,
        'info': info,
        'error': error,
    }

def _extract_filename(content_url, response):
    # get filename from Content-Disposition header if available
    if 'Content-Disposition' not in response.headers:
        return unquote(content_url.rstrip('/').split('/')[-1])
    content_disposition = response.headers['Content-Disposition']
    if 'filename=' in content_disposition:
        return unquote(content_disposition.split('filename=')[1])
    if 'filename*=' in content_disposition:
        filename_with_enc = content_disposition.split('filename*=')[1]
        if not filename_with_enc.startswith("UTF-8''"):
            raise ValueError('Invalid filename encoding: {}'.format(filename_with_enc))
        return unquote(filename_with_enc[7:])

@celery_app.task(bind=True, max_retries=1)
def import_dataset(self, user_id, node_id, dataset_url, provider, filepath):
    logger.info('Importing dataset from {} to {}/{} on {}'.format(dataset_url, provider, filepath, node_id))
    self.update_state(state='downloading dataset', meta={
        'progress': 0,
        'user': user_id,
        'node': node_id,
        'filenames': None,
    })
    response = requests.get(dataset_url)
    response.raise_for_status()
    html = BeautifulSoup(response.content, 'html.parser')
    logger.info('Downloaded dataset from {}'.format(dataset_url))
    logger.debug('HTML: {}'.format(html))
    self.update_state(state='parsing dataset', meta={
        'progress': 10,
        'user': user_id,
        'node': node_id,
        'filenames': None,
    })
    scripts = html.find_all('script', type='application/ld+json')
    if not scripts:
        raise ValueError('No JSON-LD script found in dataset')
    content_urls = []
    for script in scripts:
        dataset = json.loads(script.string)
        logger.info('Parsed dataset from {}'.format(dataset_url))
        logger.debug('Dataset: {}'.format(dataset))
        if 'distribution' not in dataset:
            raise ValueError('No distribution found in dataset')
        distributions = dataset['distribution']
        logger.info('Found {} distributions in dataset'.format(len(distributions)))
        for distribution in distributions:
            if 'contentUrl' not in distribution:
                raise ValueError('No contentUrl found in distribution')
            content_url = distribution['contentUrl']
            content_urls.append(content_url)
    if not content_urls:
        raise ValueError('No contentUrls found in dataset')
    filenames = [{
        'url': content_url,
        'filename': None,
    } for content_url in content_urls]
    self.update_state(state='checking destination', meta={
        'progress': 20,
        'user': user_id,
        'node': node_id,
        'filenames': filenames,
    })
    user_info = OSFUser.objects.get(guids___id=user_id)
    cookie = user_info.get_or_create_cookie().decode()
    files = waterbutler.get_node_info(cookie, node_id, provider, filepath)
    if files is None:
        raise ValueError('Failed to get node info')
    current_filenames = set([
        current_file['attributes']['name'] for current_file in files['data']
    ] if 'data' in files and files['data'] is not None else [])
    self.update_state(state='downloading files', meta={
        'progress': 25,
        'user': user_id,
        'node': node_id,
        'filenames': filenames,
    })
    work_dir = tempfile.mkdtemp()
    try:
        for index, content_url in enumerate(content_urls):
            logger.info('Downloading file {} from {}'.format(index, content_url))
            response = requests.get(content_url, stream=True)
            response.raise_for_status()
            response.raw.decode_content = True
            temp_filepath = os.path.join(work_dir, 'temp.dat')
            if 'Content-Length' in response.headers:
                total_size = int(response.headers['Content-Length'])
                if total_size > MAX_IMPORTABLE_DATASET_BYTES:
                    raise ValueError('Dataset too large')
            total_size = 0
            with open(temp_filepath, 'wb') as temp_file:
                for chunk in response.iter_content():
                    if total_size + len(chunk) > MAX_IMPORTABLE_DATASET_BYTES:
                        raise ValueError('Dataset too large')
                    temp_file.write(chunk)
                    total_size += len(chunk)
            filename = _extract_filename(content_url, response)
            duplicated_index = 1
            filenamebody, filenameext = os.path.splitext(filename)
            while filename in current_filenames:
                filename = '{} ({}){}'.format(filenamebody, duplicated_index, filenameext)
                duplicated_index += 1
            logger.info('Uploading file {} to {}'.format(filename, filepath))
            waterbutler.upload_file(
                cookie,
                node_id,
                temp_filepath,
                filename,
                provider + filepath,
            )
            filenames[index]['filename'] = filename
            self.update_state(state='downloading files', meta={
                'progress': 25 + 75 * (content_urls.index(content_url) + 1) / len(content_urls),
                'user': user_id,
                'node': node_id,
                'filenames': filenames,
            })
            os.unlink(temp_filepath)
        return {
            'user': user_id,
            'node': node_id,
            'filenames': filenames,
        }
    finally:
        shutil.rmtree(work_dir)
