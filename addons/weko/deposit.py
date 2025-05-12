# -*- coding: utf-8 -*-
import logging
import mimetypes
import os
import re
import shutil
import tempfile
from zipfile import ZipFile
import bagit

from framework.auth import Auth
from framework.celery_tasks import app as celery_app
from osf.models import AbstractNode, OSFUser

import json
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
    def update_task_state(state=None, meta=None):
        logger.info(f'Updating task state: {state}, {meta}')
        self.update_state(state=state, meta=meta)
    return _deposit_metadata(
        user_id, index_id, node_id, metadata_node_id,
        schema_id, file_metadatas, project_metadatas, metadata_paths, status_path, delete_after=delete_after,
        task_request_id=self.request.id,
        update_task_state=update_task_state,
    )

def _deposit_metadata(
    user_id, index_id, node_id, metadata_node_id,
    schema_id, file_metadatas, project_metadatas, metadata_paths, status_path,
    delete_after=False, delete_temp_dir_immediately=True,
    task_request_id=None, update_task_state=None,
):

    from .models import RegistrationMetadataMapping
    user = OSFUser.load(user_id)
    logger.info(f'Deposit: {metadata_paths}, {status_path} {task_request_id}')
    node = AbstractNode.load(node_id)
    weko_addon = node.get_addon(SHORT_NAME)
    weko_addon.set_publish_task_id(status_path, task_request_id)
    wb = WaterButlerClient(user).get_client_for_node(node)
    tmp_dir = None
    bagit_dir = None
    try:
        tmp_dir = tempfile.mkdtemp()
        if update_task_state:
            update_task_state(state='downloading', meta={
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
            if update_task_state:
                update_task_state(state='initializing', meta={
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
        if update_task_state:
            update_task_state(state='packaging', meta={
                'progress': 50,
                'paths': metadata_paths,
            })

        ad_metadata_paths = []
        ad_metadata_download_file_names = []
        ad_metadata_download_files = []
        ad_metadata_total_size = 0
        for metadata in project_metadatas:
            if 'choose-additional-metadata' in metadata:
                try:
                    file_list = json.loads(metadata['choose-additional-metadata']['value'])
                    ad_metadata_paths.extend(item['path'] for item in file_list)
                except (json.JSONDecodeError, KeyError) as e:
                    logger.info(f'JSONDecodeError: {e}')

        for path in ad_metadata_paths:
            if '/' not in path:
                raise ValueError(f'Malformed path: {path}')
            if update_task_state:
                update_task_state(state='initializing', meta={
                    'progress': 0,
                    'path': path,
                })
            materialized_path = path[path.index('/'):]
            file = wb.get_file_by_materialized_path(path)
            logger.debug(f'File: {file}, size={file.size}')
            if file is None:
                raise KeyError(f'File not found: {materialized_path}')
            download_file_path, download_file_type = _download(node, file, tmp_dir, ad_metadata_total_size)
            filesize = os.path.getsize(download_file_path)
            ad_metadata_total_size += filesize
            _, download_file_name = os.path.split(download_file_path)
            ad_metadata_download_file_names.append((download_file_name, download_file_type))
            ad_metadata_download_files.append(file)
        if update_task_state:
            update_task_state(state='packaging', meta={
                'progress': 50,
                'paths': path,
            })

        c = weko_addon.create_client()
        target_index = c.get_index_by_id(index_id)
        # target_index = ''

        # Packaging the files as BagIt
        bagit_dir = tempfile.mkdtemp()
        bagit_metadata = {
            'Contact-Name': user.fullname,
            'Contact-Email': user.username,
        }
        if user.affiliated_institutions and user.affiliated_institutions.first():
            bagit_metadata['Source-Organization'] = user.affiliated_institutions.first().name
        bag = bagit.make_bag(bagit_dir, bagit_metadata)

        for download_file_name, _ in download_file_names:
            file_in_bagit_path = os.path.join(bagit_dir, 'data', 'files', download_file_name)
            os.makedirs(os.path.dirname(file_in_bagit_path), exist_ok=True)
            shutil.copyfile(os.path.join(tmp_dir, download_file_name), file_in_bagit_path)

        for download_file_name, _ in ad_metadata_download_file_names:
            file_in_bagit_path = os.path.join(bagit_dir, 'data', 'files', download_file_name)
            os.makedirs(os.path.dirname(file_in_bagit_path), exist_ok=True)
            shutil.copyfile(os.path.join(tmp_dir, download_file_name), file_in_bagit_path)

        # Metadata as CSV
        mapping_def_csv = RegistrationMetadataMapping.objects.filter(
            registration_schema_id=schema_id,
            filename__in=['index.csv', None],
        ).first()
        if mapping_def_csv is not None:
            with open(os.path.join(bagit_dir, 'data', 'index.csv'), 'w', encoding='utf8') as f:
                schema.write_csv(
                    user,
                    f,
                    target_index,
                    download_file_names,
                    schema_id,
                    file_metadatas,
                    project_metadatas,
                )
        # Metadata as RO-Crate
        mapping_def_ro_crate_json = RegistrationMetadataMapping.objects.filter(
            registration_schema_id=schema_id,
            filename='ro-crate-metadata.json',
        ).first()
        if mapping_def_ro_crate_json is not None:
            with open(os.path.join(bagit_dir, 'data', 'ro-crate-metadata.json'), 'w', encoding='utf8') as f:
                schema.write_ro_crate_json(
                    user,
                    f,
                    target_index,
                    download_file_names,
                    schema_id,
                    file_metadatas,
                    project_metadatas,
                )
        if mapping_def_csv is None and mapping_def_ro_crate_json is None:
            logger.warning('No metadata mapping found')
        bag.save(manifests=True)

        zip_path = os.path.join(tmp_dir, 'payload.zip')
        with ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(bagit_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, bagit_dir))

        headers = {
            'Packaging': 'http://purl.org/net/sword/3.0/package/SimpleZip',
            'Content-Disposition': 'attachment; filename=payload.zip',
        }
        files = {
            'file': ('payload.zip', open(zip_path, 'rb'), 'application/zip'),
        }
        if update_task_state:
            update_task_state(state='uploading', meta={
                'progress': 60,
                'paths': metadata_paths,
            })
        logger.info(f'Uploading... {file_metadatas}')
        respbody = c.deposit(files, headers=headers)
        logger.info(f'Uploaded: {respbody}')

        if update_task_state:
            update_task_state(state='uploaded', meta={
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
                    'item_html_url': links[0]['@id'] if len(links) > 0 else None,
                },
            )
        for file in ad_metadata_download_files:
            if delete_after:
                file.delete()
            weko_addon.create_waterbutler_deposit_log(
                Auth(user),
                'item_deposited',
                {
                    'materialized': file.materialized,
                    'path': file.path,
                    'item_html_url': links[0]['@id'] if len(links) > 0 else None,
                },
            )
        return {
            'result': links[0]['@id'] if len(links) > 0 else None,
            'paths': metadata_paths,
        }
    finally:
        if delete_temp_dir_immediately and tmp_dir and os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        if delete_temp_dir_immediately and bagit_dir and os.path.exists(bagit_dir):
            shutil.rmtree(bagit_dir)
