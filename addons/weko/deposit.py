# -*- coding: utf-8 -*-
import io
import logging
import mimetypes
import os
import re
import shutil
import tempfile
from zipfile import ZipFile

from framework.auth import Auth
from framework.celery_tasks import app as celery_app
from osf.models import AbstractNode, OSFUser

from addons.metadata.packages import WaterButlerClient, BaseROCrateFactory
from .apps import SHORT_NAME
from . import schema
from . import settings


logger = logging.getLogger('addons.weko.views')

ROCRATE_DATASET_MIME_TYPE = 'application/rdm-dataset'
ROCRATE_PROJECT_MIME_TYPE = 'application/rdm-project'
ROCRATE_FILENAME_PATTERN = re.compile(r'\.rdm-project([^\.]+)\.zip$')

class ROCrateFactory(BaseROCrateFactory):

    def __init__(self, node, work_dir, folder):
        super(ROCrateFactory, self).__init__(node, work_dir)
        self.folder = folder

    def _build_ro_crate(self, crate):
        user_ids = {}
        schema_ids = {}
        comment_ids = {}
        files = []
        for file in self.folder.get_files():
            _, children = self._create_file_entities(crate, self.node, f'./', file, user_ids, schema_ids, comment_ids)
            files += children
        for _, _, comments in files:
            crate.add(*comments)
        return crate, files


def _download(node, file, tmp_dir, total_size):
    if file.kind == 'file':
        _check_file_size(total_size + int(file.size))
        download_file_path = os.path.join(tmp_dir, file.name)
        with open(os.path.join(download_file_path), 'wb') as f:
            file.download_to(f)
        if ROCRATE_FILENAME_PATTERN.match(file.name):
            mtype = ROCRATE_PROJECT_MIME_TYPE
        else:
            mtype, _ = mimetypes.guess_type(download_file_path)
        filesize = os.path.getsize(download_file_path)
        if filesize != int(file.size):
            raise IOError(f'File size mismatch: {filesize} != {file.size}')
        return download_file_path, mtype
    rocrate = ROCrateFactory(node, tmp_dir, file)
    download_file_path = os.path.join(tmp_dir, 'rocrate.zip')
    rocrate.download_to(download_file_path)
    return download_file_path, ROCRATE_DATASET_MIME_TYPE

def _check_file_size(total_size):
    if total_size <= settings.MAX_UPLOAD_SIZE:
        return
    params = f'exported={total_size}, limit={settings.MAX_UPLOAD_SIZE}'
    raise IOError(f'Exported file size exceeded limit: {params}')

@celery_app.task(bind=True, max_retries=5, default_retry_delay=60)
def deposit_metadata(
    self, user_id, index_id, node_id, metadata_node_id,
    schema_id, file_metadatas, project_metadatas, metadata_paths, status_path, delete_after=False,
):
    user = OSFUser.load(user_id)
    logger.info(f'Deposit: {metadata_paths}, {status_path} {self.request.id}')
    node = AbstractNode.load(node_id)
    weko_addon = node.get_addon(SHORT_NAME)
    weko_addon.set_publish_task_id(status_path, self.request.id)
    wb = WaterButlerClient(user).get_client_for_node(node)
    tmp_dir = None
    try:
        tmp_dir = tempfile.mkdtemp()
        self.update_state(state='downloading', meta={
            'progress': 10,
            'paths': metadata_paths,
        })
        download_file_names = []
        download_files = []
        total_size = 0
        for metadata_path in metadata_paths:
            path = metadata_path
            if '/' not in path:
                raise ValueError(f'Malformed path: {path}')
            self.update_state(state='initializing', meta={
                'progress': 0,
                'path': metadata_path,
            })
            materialized_path = path[path.index('/'):]
            file = wb.get_file_by_materialized_path(path)
            logger.debug(f'File: {file}, size={file.size}')
            if file is None:
                raise KeyError(f'File not found: {materialized_path}')
            download_file_path, download_file_type = _download(node, file, tmp_dir, total_size)
            filesize = os.path.getsize(download_file_path)
            total_size += filesize
            _, download_file_name = os.path.split(download_file_path)
            download_file_names.append((download_file_name, download_file_type))
            download_files.append(file)
            logger.info(f'Downloaded: {download_file_path} {filesize}')
        self.update_state(state='packaging', meta={
            'progress': 50,
            'paths': metadata_paths,
        })

        c = weko_addon.create_client()
        target_index = c.get_index_by_id(index_id)

        zip_path = os.path.join(tmp_dir, 'payload.zip')
        with ZipFile(zip_path, 'w') as zf:
            for download_file_name, _ in download_file_names:
                with zf.open(os.path.join('data/', download_file_name), 'w') as df:
                    with open(download_file_path, 'rb') as sf:
                        shutil.copyfileobj(sf, df)
            with zf.open('data/index.csv', 'w') as f:
                with io.TextIOWrapper(f, encoding='utf8') as tf:
                    schema.write_csv(
                        user,
                        tf,
                        target_index,
                        download_file_names,
                        schema_id,
                        file_metadatas,
                        project_metadatas,
                    )
        headers = {
            'Packaging': 'http://purl.org/net/sword/3.0/package/SimpleZip',
            'Content-Disposition': 'attachment; filename=payload.zip',
        }
        files = {
            'file': ('payload.zip', open(zip_path, 'rb'), 'application/zip'),
        }
        self.update_state(state='uploading', meta={
            'progress': 60,
            'paths': metadata_paths,
        })
        logger.info(f'Uploading... {file_metadatas}')
        respbody = c.deposit(files, headers=headers)
        logger.info(f'Uploaded: {respbody}')
        self.update_state(state='uploaded', meta={
            'progress': 100,
            'paths': metadata_paths,
        })
        links = [l for l in respbody['links'] if 'contentType' in l and '@id' in l and l['contentType'] == 'text/html']
        for file in download_files:
            if delete_after:
                file.delete()
            weko_addon.create_waterbutler_deposit_log(
                Auth(user),
                'item_deposited',
                {
                    'materialized': file.materialized,
                    'path': file.path,
                    'item_html_url': links[0]['@id'],
                },
            )
        return {
            'result': links[0]['@id'] if len(links) > 0 else None,
            'paths': metadata_paths,
        }
    finally:
        if tmp_dir and os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
