# -*- coding: utf-8 -*-
'''Common functions for timestamp.
'''
from __future__ import absolute_import
import datetime
import hashlib
import logging
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
import traceback

from urllib3.util.retry import Retry
import requests

from api.base import settings as api_settings
from api.base.utils import waterbutler_api_url_for
from celery.contrib.abortable import AbortableTask, AbortableAsyncResult
from django.utils import timezone
from osf.models import (
    AbstractNode, BaseFileNode, Guid, RdmFileTimestamptokenVerifyResult, RdmUserKey,
    OSFUser, TimestampTask
)
from website import util
from website import settings
from website.util import waterbutler

from django.contrib.contenttypes.models import ContentType
from framework.celery_tasks import app as celery_app
from inspect import currentframe

logger = logging.getLogger(__name__)

RESULT_MESSAGE = {
    api_settings.TIME_STAMP_TOKEN_CHECK_NG:
        api_settings.TIME_STAMP_TOKEN_CHECK_NG_MSG,  # 'NG'
    api_settings.TIME_STAMP_TOKEN_NO_DATA:
        api_settings.TIME_STAMP_TOKEN_NO_DATA_MSG,  # 'TST missing(Retrieving Failed)'
    api_settings.TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND:
        api_settings.TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND_MSG,  # 'TST missing(Unverify)'
    api_settings.FILE_NOT_EXISTS:
        api_settings.FILE_NOT_EXISTS_MSG,  # 'FILE missing'
    api_settings.TIME_STAMP_VERIFICATION_ERR:
        api_settings.TIME_STAMP_VERIFICATION_ERR_MSG,
    api_settings.TIME_STAMP_STORAGE_DISCONNECTED:
        api_settings.TIME_STAMP_STORAGE_DISCONNECTED_MSG,
    api_settings.TIME_STAMP_STORAGE_NOT_ACCESSIBLE:
        api_settings.TIME_STAMP_STORAGE_NOT_ACCESSIBLE_MSG,
}

STATUS_NOT_ACCESSIBLE = [
    api_settings.FILE_NOT_EXISTS,
    api_settings.FILE_NOT_FOUND,
    api_settings.TIME_STAMP_VERIFICATION_ERR,
    api_settings.TIME_STAMP_STORAGE_DISCONNECTED,
    api_settings.TIME_STAMP_STORAGE_NOT_ACCESSIBLE
]

FILE_TYPE_DICT = {
    'box': 'addons.box.models.BoxFile',
    'googledrive': 'addons.googledrive.models.GoogleDriveFile',
    'nextcloud': 'addons.nextcloud.models.NextcloudFile',
    'osfstorage': 'addons.osfstorage.models.OsfStorageFile',
    'owncloud': 'addons.owncloud.models.OwncloudFile',
    's3': 'addons.s3.models.S3File',
    's3compat': 'addons.s3compat.models.S3CompatFile',
    'swift': 'addons.swift.models.SwiftFile',
    'github': 'addons.github.models.GithubFile',
}

class OSFAbortableAsyncResult(AbortableAsyncResult):
    """This class is a workaround to a celery bug that throws an AttributeError when it
    should not.

    The bug itself has been fixed in the celery's PR #5435, but it will only be released
    on celery 4.4.0. And because of another bug, seems that even after the 4.4.0 release,
    we won't be able to upgrade celery.

    So for now we're fixing the bug with this class.
    """
    def ready(self):
        try:
            return super(OSFAbortableAsyncResult, self).ready()
        except AttributeError as e:
            logger.error('Failed to get task status! Exception message:')
            logger.error(str(e))
            return True


def get_async_task_data(node):
    task_data = {
        'ready': True,
        'requester': None
    }
    timestamp_task = TimestampTask.objects.filter(node=node).first()
    if timestamp_task is not None:
        task = OSFAbortableAsyncResult(timestamp_task.task_id)
        task_data['ready'] = task.ready()
        task_data['requester'] = timestamp_task.requester.username
        if task_data['ready']:
            TimestampTask.objects.filter(node=node).delete()
    return task_data

def get_error_list(pid):
    '''Retrieve from the database the list of all timestamps that has an error.
    '''
    data_list = RdmFileTimestamptokenVerifyResult.objects.filter(project_id=pid).order_by('provider', 'path')
    provider_error_list = []
    provider = None
    error_list = []

    for data in data_list:
        if data.inspection_result_status == api_settings.TIME_STAMP_TOKEN_CHECK_SUCCESS:
            continue

        if not provider:
            provider = data.provider
        elif provider != data.provider:
            provider_error_list.append({'provider': provider, 'error_list': error_list})
            provider = data.provider
            error_list = []

        if data.inspection_result_status in RESULT_MESSAGE:
            verify_result_title = RESULT_MESSAGE[data.inspection_result_status]
        else:  # 'FILE missing(Unverify)'
            verify_result_title = api_settings.FILE_NOT_FOUND_MSG

        # User and date of the verification
        if data.verify_date is not None:
            verify_date = data.verify_date.strftime('%Y/%m/%d %H:%M:%S %Z')
        else:
            verify_date = ''

        # Get file info
        base_file_data = BaseFileNode.objects.filter(_id=data.file_id)
        base_file_data_exists = base_file_data.exists()
        file_versions = None
        if base_file_data_exists:
            base_file_data = base_file_data.get()
            file_versions = base_file_data.versions.all()

        # Get creator info
        creator = None
        if data.upload_file_modified_user is not None:
            creator = OSFUser.objects.get(id=data.upload_file_modified_user)
        elif data.upload_file_created_user is not None:
            creator = OSFUser.objects.get(id=data.upload_file_created_user)
        elif file_versions is not None and file_versions.exists():
            creator = file_versions.latest('id').creator

        # Change None to '' (empty string)
        data.path = '' if data.path is None else data.path
        data.upload_file_created_at = '' if data.upload_file_created_at is None else \
            data.upload_file_created_at
        data.verify_file_created_at = '' if data.verify_file_created_at is None else \
            data.verify_file_created_at
        data.upload_file_modified_at = '' if data.upload_file_modified_at is None else \
            data.upload_file_modified_at
        data.verify_file_modified_at = '' if data.verify_file_modified_at is None else \
            data.verify_file_modified_at
        data.upload_file_size = '' if data.upload_file_size is None else \
            data.upload_file_size
        data.verify_file_size = '' if data.verify_file_size is None else \
            data.verify_file_size

        # Generate error_info dictionary
        error_info = {
            'creator_name': '',
            'creator_email': '',
            'creator_id': '',
            'file_path': data.path,
            'file_id': data.file_id,
            'file_create_date_on_upload': data.upload_file_created_at,
            'file_create_date_on_verify': data.verify_file_created_at,
            'file_modify_date_on_upload': data.upload_file_modified_at,
            'file_modify_date_on_verify': data.verify_file_modified_at,
            'file_size_on_upload': data.upload_file_size,
            'file_size_on_verify': data.verify_file_size,
            'file_version': '',
            'project_id': data.project_id,
            'organization_id': '',
            'organization_name': '',
            'verify_user_id': '',
            'verify_user_name': '',
            'verify_date': verify_date,
            'verify_result_title': verify_result_title,
        }

        try:
            verify_user = OSFUser.objects.get(id=data.verify_user)
            error_info['verify_user_id'] = verify_user._id
            error_info['verify_user_name'] = verify_user.fullname
        except OSFUser.DoesNotExist:
            logger.warning('Timestamp Control: verify_user not found.')

        if base_file_data_exists and provider == 'osfstorage':
            error_info['file_version'] = base_file_data.current_version_number

        if creator is not None:
            error_info['creator_name'] = creator.fullname
            error_info['creator_email'] = creator.username
            error_info['creator_id'] = creator._id

            institution = creator.affiliated_institutions.first()
            if institution is not None:
                error_info['organization_id'] = institution._id
                error_info['organization_name'] = institution.name

        error_list.append(error_info)

    if error_list:
        provider_error_list.append({'provider': provider, 'error_list': error_list})

    return provider_error_list

def get_full_list(uid, pid, node):
    '''Get a full list of timestamps from all files uploaded to a storage.
    '''
    user_info = OSFUser.objects.get(id=uid)
    cookie = user_info.get_or_create_cookie()

    api_url = util.api_v2_url('nodes/{}/files'.format(pid))
    headers = {'content-type': 'application/json'}
    cookies = {settings.COOKIE_NAME: cookie}

    file_res = requests.get(api_url, headers=headers, cookies=cookies)
    provider_json_res = file_res.json()
    file_res.close()
    provider_list = []

    for provider_data in provider_json_res['data']:
        provider = provider_data['attributes']['provider']
        waterbutler_json_res = waterbutler.get_node_info(cookie, pid, provider, '/')

        if waterbutler_json_res is None:
            provider_files = RdmFileTimestamptokenVerifyResult.objects.filter(
                project_id=node._id,
                provider=provider
            )
            files_status = provider_files.first().inspection_result_status
            if files_status != api_settings.TIME_STAMP_STORAGE_DISCONNECTED:
                not_accessible_status = api_settings.TIME_STAMP_STORAGE_NOT_ACCESSIBLE
                provider_files.update(inspection_result_status=not_accessible_status)
            continue
        else:
            RdmFileTimestamptokenVerifyResult.objects.filter(
                project_id=node._id,
                provider=provider,
                inspection_result_status=api_settings.FILE_NOT_EXISTS
            ).update(inspection_result_status=api_settings.FILE_NOT_EXISTS)

        file_list = []
        child_file_list = []
        for file_data in waterbutler_json_res['data']:
            if file_data['attributes']['kind'] == 'folder':
                child_file_list.extend(
                    waterbutler_folder_file_info(
                        pid,
                        provider_data['attributes']['provider'],
                        file_data['attributes']['path'],
                        node, cookies, headers
                    )
                )
            else:
                file_info = None
                basefile_node = BaseFileNode.resolve_class(
                    provider_data['attributes']['provider'],
                    BaseFileNode.FILE
                ).get_or_create(
                    node,
                    file_data['attributes']['path']
                )
                basefile_node.materialized_path = file_data['attributes']['materialized']
                basefile_node.name = os.path.basename(file_data['attributes']['materialized'])
                basefile_node.save()
                file_info = {
                    'file_id': basefile_node._id,
                    'file_name': file_data['attributes'].get('name'),
                    'file_path': file_data['attributes'].get('materialized'),
                    'size': file_data['attributes'].get('size'),
                    'created': file_data['attributes'].get('created_utc'),
                    'modified': file_data['attributes'].get('modified_utc'),
                    'file_version': ''
                }
                if provider_data['attributes']['provider'] == 'osfstorage':
                    file_info['file_version'] = file_data['attributes']['extra'].get('version')
                if file_info:
                    file_list.append(file_info)

        file_list.extend(child_file_list)

        if file_list:
            provider_files = {
                'provider': provider_data['attributes']['provider'],
                'provider_file_list': file_list
            }
            provider_list.append(provider_files)

    return provider_list

def check_file_timestamp(uid, node, data):
    logger.critical('1')
    user = OSFUser.objects.get(id=uid)
    cookie = user.get_or_create_cookie()
    tmp_dir = None
    result = None
    logger.critical('2')
    try:
        logger.critical('3')
        file_node = BaseFileNode.objects.get(_id=data['file_id'])
        tmp_dir = tempfile.mkdtemp()
        logger.critical('4')
        if not os.path.exists(tmp_dir):
            logger.critical('5')
            os.mkdir(tmp_dir)
        logger.critical('6')
        download_file_path = waterbutler.download_file(cookie, file_node, tmp_dir)
        logger.critical(file_node)
        logger.critical('7')
        if download_file_path is None:
            intentional_remove_status = [
                api_settings.FILE_NOT_EXISTS,
                api_settings.TIME_STAMP_STORAGE_DISCONNECTED
            ]
            logger.critical('8')
            file_data = RdmFileTimestamptokenVerifyResult.objects.filter(file_id=data['file_id'])
            if file_data.exists() and \
                    file_data.get().inspection_result_status not in intentional_remove_status:
                file_data.update(inspection_result_status=api_settings.FILE_NOT_FOUND)
                logger.critical('9')
            return None
            logger.critical('10')
        if not userkey_generation_check(user._id):
            logger.critical('11')
            userkey_generation(user._id)
            logger.critical('12')
        verify_check = TimeStampTokenVerifyCheck()
        logger.critical('13')
        result = verify_check.timestamp_check(
            user._id, data, node._id, download_file_path, tmp_dir
        )
        logger.critical('14')

        shutil.rmtree(tmp_dir)
        logger.critical('15')
        return result

    except Exception as err:
        logger.critical('16')
        if tmp_dir and os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        logger.exception(err)
        raise

@celery_app.task(bind=True, base=AbortableTask)
def celery_verify_timestamp_token(self, uid, node_id):
    secs_to_wait = 60.0 / api_settings.TS_REQUESTS_PER_MIN
    last_run = None

    celery_app.current_task.update_state(state='PROGRESS', meta={'progress': 0})
    node = AbstractNode.objects.get(id=node_id)
    celery_app.current_task.update_state(state='PROGRESS', meta={'progress': 50})
    for provider_dict in get_full_list(uid, node._id, node):
        for p_item in provider_dict['provider_file_list']:
            if self.is_aborted():
                break
            p_item['provider'] = provider_dict['provider']
            last_run = time.time()
            result = check_file_timestamp(uid, node, p_item)
            if result is None:
                continue
            # Do not let the task run too many requests
            while time.time() < last_run + secs_to_wait:
                time.sleep(0.1)
    if self.is_aborted():
        logger.warning('Task from project ID {} was cancelled by user ID {}'.format(node_id, uid))
    celery_app.current_task.update_state(state='SUCCESS', meta={'progress': 100})

@celery_app.task(bind=True, base=AbortableTask)
def celery_add_timestamp_token(self, uid, node_id, request_data):
    """Celery Timestamptoken add method
    """
    secs_to_wait = 60.0 / api_settings.TS_REQUESTS_PER_MIN
    last_run = None

    node = AbstractNode.objects.get(id=node_id)
    for _, data in enumerate(request_data):
        if self.is_aborted():
            break
        last_run = time.time()
        result = add_token(uid, node, data)
        if result is None:
            continue
        # Do not let the task run too many requests
        while time.time() < last_run + secs_to_wait:
            time.sleep(0.1)
    if self.is_aborted():
        logger.warning('Task from project ID {} was cancelled by user ID {}'.format(node_id, uid))

def get_celery_task(node):
    task = None
    timestamp_task = TimestampTask.objects.filter(node=node).first()
    if timestamp_task is not None:
        task = OSFAbortableAsyncResult(timestamp_task.task_id)
    return task

def get_celery_task_progress(node):
    status = {
        'ready': True
    }
    task = get_celery_task(node)
    if task is not None:
        status['ready'] = task.ready()
        if status['ready']:
            TimestampTask.objects.filter(node=node).delete()
    return status

def cancel_celery_task(node):
    result = {
        'success': False,
    }
    task = get_celery_task(node)
    if task is not None and not task.ready():
        task.revoke()
        task.abort()
        result['success'] = True
    TimestampTask.objects.filter(node=node).delete()
    return result

def add_token(uid, node, data):
    user = OSFUser.objects.get(id=uid)
    cookie = user.get_or_create_cookie()
    tmp_dir = None

    file_node = BaseFileNode.objects.get(_id=data['file_id'])

    # Check access to provider
    root_file_nodes = waterbutler.get_node_info(cookie, node._id, data['provider'], '/')
    if root_file_nodes is None:
        return None

    try:
        # Request To Download File
        tmp_dir = tempfile.mkdtemp()
        download_file_path = waterbutler.download_file(cookie, file_node, tmp_dir)
        if download_file_path is None:
            intentional_remove_status = [
                api_settings.FILE_NOT_EXISTS,
                api_settings.TIME_STAMP_STORAGE_DISCONNECTED
            ]
            try:
                file_data = RdmFileTimestamptokenVerifyResult.objects.get(file_id=data['file_id'])
                if file_data.inspection_result_status not in intentional_remove_status:
                    file_data.inspection_result_status = api_settings.defaults.FILE_NOT_FOUND
                    file_data.save()
            except RdmFileTimestamptokenVerifyResult.DoesNotExist:
                pass
            return None
        if not userkey_generation_check(user._id):
            userkey_generation(user._id)

        addTimestamp = AddTimestamp()
        result = addTimestamp.add_timestamp(
            user._id, data, node._id, download_file_path, tmp_dir
        )

        shutil.rmtree(tmp_dir)
        return result

    except Exception as err:
        if tmp_dir and os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        logger.exception(err)
        raise

def get_file_info(cookie, file_node, version):
    headers = {'content-type': 'application/json'}
    file_data_request = requests.get(
        file_node.generate_waterbutler_url(
            version=version.identifier, meta='', _internal=True
        ), headers=headers, cookies={settings.COOKIE_NAME: cookie}
    )
    if file_data_request.status_code == 200:
        file_data = file_data_request.json().get('data')
        file_info = {
            'provider': file_node.provider,
            'file_id': file_node._id,
            'file_name': file_data['attributes'].get('name'),
            'file_path': file_data['attributes'].get('materialized'),
            'size': file_data['attributes'].get('size'),
            'created': file_data['attributes'].get('created_utc'),
            'modified': file_data['attributes'].get('modified_utc'),
            'version': ''
        }
        if file_node.provider == 'osfstorage':
            file_info['version'] = file_data['attributes']['extra'].get('version')
        return file_info
    return None

def file_created_or_updated(node, metadata, user_id, created_flag):
    if metadata['provider'] != 'osfstorage':
        file_node = BaseFileNode.resolve_class(
            metadata['provider'], BaseFileNode.FILE
        ).get_or_create(node, '/' + metadata.get('path').lstrip('/'))
        file_node.path = '/' + metadata.get('path').lstrip('/')
        file_node.name = metadata.get('name')
        file_node.materialized_path = metadata.get('materialized')

        file_node.save()
        logger.critical('Create or update............................')
        logger.critical(file_node.id)
        logger.critical(file_node.type)
        logger.critical(file_node.provider)

        metadata['path'] = file_node._id
    created_at = metadata.get('created_utc')
    modified_at = metadata.get('modified_utc')
    version = ''
    if not created_at:
        created_at = None
    if not modified_at:
        modified_at = None
    if metadata['provider'] == 'osf_storage':
        version = metadata['extra'].get('version')
    file_info = {
        'file_id': metadata.get('path'),
        'file_name': metadata.get('name'),
        'file_path': metadata.get('materialized'),
        'size': metadata.get('size'),
        'created': created_at,
        'modified': modified_at,
        'version': version,
        'provider': metadata.get('provider')
    }
    add_token(user_id, node, file_info)

    # Update created/modified user in timestamp result
    verify_data = RdmFileTimestamptokenVerifyResult.objects.get(file_id=file_info['file_id'])
    if created_flag:
        verify_data.upload_file_created_user = user_id
    else:  # Updated
        verify_data.upload_file_modified_user = user_id
    verify_data.upload_file_created_at = file_info['created']
    verify_data.upload_file_modified_at = file_info['modified']
    verify_data.upload_file_size = file_info['size']
    verify_data.save()

def file_node_moved(uid, project_id, src_provider, dest_provider, src_path, dest_path, metadata):
    from pprint import pprint
    pprint(metadata)
    pprint(get_linenumber())
    src_path = src_path if src_path[0] == '/' else '/' + src_path
    dest_path = dest_path if dest_path[0] == '/' else '/' + dest_path
    target_object_id = Guid.objects.get(_id=project_id,
                                        content_type_id=ContentType.objects.get_for_model(AbstractNode).id).object_id
    deleted_files = RdmFileTimestamptokenVerifyResult.objects.filter(
        path__startswith=dest_path,
        project_id=project_id,
        provider=dest_provider
    ).exclude(
        inspection_result_status=api_settings.FILE_NOT_EXISTS
    ).all()
    pprint(get_linenumber())
    for deleted_file in deleted_files:
        file_node_overwitten(project_id, target_object_id, dest_provider, dest_path)
    pprint(get_linenumber())
    moved_files = RdmFileTimestamptokenVerifyResult.objects.filter(
        path__startswith=src_path,
        project_id=project_id,
        provider=src_provider
    ).exclude(
        inspection_result_status__in=STATUS_NOT_ACCESSIBLE
    ).all()
    pprint(get_linenumber())
    for moved_file in moved_files:
        moved_file.path = moved_file.path.replace(src_path, dest_path, 1)
        moved_file.provider = dest_provider
        moved_file.save()
        pprint(get_linenumber())
    if src_provider != 'osfstorage' and src_path[-1:] == '/':
        pprint(get_linenumber())
        logger.critical('src_provider != and src_path[-1:] == ')
        file_nodes = BaseFileNode.objects.filter(target_object_id=target_object_id,
                                                 provider=src_provider,
                                                 deleted_on__isnull=True,
                                                 _path__startswith=src_path).all()
        for file_node in file_nodes:
            file_node._path = re.sub(r'^' + src_path, dest_path, file_node._path)
            file_node._materialized_path = re.sub(r'^' + src_path, dest_path, file_node._path)
            logger.critical(file_node.id)
            logger.critical(file_node.type)
            logger.critical(file_node.provider)
            file_node.type = move_file_node_update(file_node, src_provider, dest_provider, metadata)
            if dest_provider == 'osfstorage' and src_provider != 'box':
                file_node.delete()
                rft = RdmFileTimestamptokenVerifyResult.objects.filter(file_id=file_node._id).first()
                file_node = BaseFileNode.objects.filter(name=file_node.name).order_by('-id').first()
                rft.file_id = file_node._id
                rft.provider = 'osfstorage'
                rft.save()
                logger.critical(file_node.id)
                logger.critical(file_node.type)
                logger.critical(file_node.provider)
            if src_provider == 'box':
                logger.critical(file_node.id)
                rft = RdmFileTimestamptokenVerifyResult.objects.filter(provider=dest_provider, path=dest_path).first()
                new_file_id = BaseFileNode.objects.filter(provider=dest_provider, _path=dest_path).first()._id
                # file_node = BaseFileNode.objects.filter(name=file_node.name).order_by('-id').first()
                rft.file_id = new_file_id
                # rft.provider = 'box'
                rft.save()
                logger.critical(file_node.id)
                logger.critical(file_node.type)
                logger.critical(file_node.provider)
            provider_change_update_timestampverification(uid, file_node, src_provider, dest_provider)

    else:
        pprint(get_linenumber())
        file_nodes = BaseFileNode.objects.filter(target_object_id=target_object_id,
                                                 provider=src_provider,
                                                 deleted_on__isnull=True,
                                                 _path=src_path).all()
        if len(file_nodes) == 0:
            if src_provider == 'box':
                pprint(get_linenumber())
                logger.critical(file_node.id)
                rft = RdmFileTimestamptokenVerifyResult.objects.filter(provider=dest_provider, path=dest_path).first()
                pprint(get_linenumber())
                new_file_id = BaseFileNode.objects.filter(provider=dest_provider, _path=dest_path).first()._id
                pprint(get_linenumber())
                # file_node = BaseFileNode.objects.filter(name=file_node.name).order_by('-id').first()
                rft.file_id = new_file_id
                pprint(get_linenumber())
                # rft.provider = 'box'
                rft.save()
                pprint(get_linenumber())
                logger.critical(file_node.id)
                logger.critical(file_node.type)
                logger.critical(file_node.provider)
        pprint(get_linenumber())
        for file_node in file_nodes:
            pprint(get_linenumber())
            file_node._path = dest_path
            file_node._materialized_path = dest_path
            logger.critical(file_node.id)
            logger.critical(file_node.type)
            logger.critical(file_node.provider)
            pprint(get_linenumber())
            file_node = move_file_node_update(file_node, src_provider, dest_provider, metadata)
            pprint(get_linenumber())
            if dest_provider == 'osfstorage' and src_provider != 'box':
                pprint(get_linenumber())
                file_node.delete()
                rft = RdmFileTimestamptokenVerifyResult.objects.filter(file_id=file_node._id).first()
                pprint(get_linenumber())
                file_node = BaseFileNode.objects.filter(name=file_node.name).order_by('-id').first()
                pprint(get_linenumber())
                rft.file_id = file_node._id
                rft.provider = 'osfstorage'
                rft.save()
                pprint(get_linenumber())
                logger.critical(file_node.id)
                logger.critical(file_node.type)
                logger.critical(file_node.provider)
            provider_change_update_timestampverification(uid, file_node, src_provider, dest_provider)
    if src_provider == 'osfstorage' and dest_provider != 'osfstorage':
        pprint(get_linenumber())
        node = AbstractNode.objects.get(pk=Guid.objects.filter(_id=metadata['node']['_id']).first().object_id)
        pprint(get_linenumber())
        file_created_or_updated(node, metadata, uid, False)
        pprint(get_linenumber())

def move_file_node_update(file_node, src_provider, dest_provider, metadata=None):
    from pprint import pprint
    pprint(metadata['path'])
    pprint(get_linenumber())
    file_node.type = file_node.type.replace(src_provider, dest_provider)
    pprint(get_linenumber())
    dest_file_type = dynamic_import(FILE_TYPE_DICT[dest_provider])
    pprint(get_linenumber())
    file_node.__class__ = dest_file_type
    pprint(get_linenumber())
    file_node.type = 'osf.{}file'.format(dest_provider)
    pprint(get_linenumber())
    file_node.provider = dest_provider
    pprint(get_linenumber())
    file_node._meta.model._provider = dest_provider
    pprint(get_linenumber())
    path = metadata.get('path', None)
    pprint(get_linenumber())
    pprint(path)
    pprint(get_linenumber())
    if path is not None and path is not '' and dest_provider != 'osfstorage':
        file_node.path = path
    file_node.save()
    pprint(get_linenumber())
    logger.critical(file_node.id)
    logger.critical(file_node.type)
    logger.critical(file_node.provider)
    return file_node
def get_linenumber():
    cf = currentframe()
    return cf.f_back.f_lineno

def dynamic_import(name):
    components = name.split('.')
    mod = __import__(components[0])
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

def provider_change_update_timestampverification(uid, file_node, src_provider, dest_provider):
    last_timestamp_result = RdmFileTimestamptokenVerifyResult.objects.get(file_id=file_node._id)
    path = file_node.materialized_path
    if src_provider != dest_provider:
        file_info = {
            'file_id': file_node._id,
            'file_name': file_node.name,
            'file_path': path,
            'created': file_node.created,
            'modified': file_node.modified,
            'provider': file_node.provider,
            'size': last_timestamp_result.verify_file_size,
        }
        if dest_provider == 'osfstorage':
            file_info['version'] = 1
        res = check_file_timestamp(uid, file_node.target, file_info)
        return res

def file_node_overwitten(project_id, target_object_id, addon_name, src_path):
    src_path = src_path if src_path[0] == '/' else '/' + src_path
    RdmFileTimestamptokenVerifyResult.objects.filter(
        project_id=project_id,
        provider=addon_name,
        path__startswith=src_path
    ).delete()
    if addon_name != 'osfstorage':
        if src_path[-1:] == '/':
            file_nodes = BaseFileNode.objects.filter(target_object_id=target_object_id,
                                                     provider=addon_name,
                                                     deleted_on__isnull=True,
                                                     _path__startswith=src_path).all()
        else:
            file_nodes = BaseFileNode.objects.filter(target_object_id=target_object_id,
                                                     provider=addon_name,
                                                     deleted_on__isnull=True,
                                                     _path=src_path).all()
        for file_node in file_nodes:
            file_node.delete()

def file_node_deleted(project_id, addon_name, src_path):
    src_path = src_path if src_path[0] == '/' else '/' + src_path

    tst_status = api_settings.FILE_NOT_EXISTS
    if src_path == '/':
        tst_status = api_settings.TIME_STAMP_STORAGE_DISCONNECTED
    RdmFileTimestamptokenVerifyResult.objects.filter(
        project_id=project_id,
        provider=addon_name,
        path__startswith=src_path
    ).exclude(
        inspection_result_status=api_settings.FILE_NOT_EXISTS
    ).update(inspection_result_status=tst_status)

def file_node_gone(project_id, addon_name, src_path):
    if project_id is None or addon_name is None or src_path is None:
        return

    src_path = src_path if src_path[0] == '/' else '/' + src_path

    tst_status = api_settings.FILE_NOT_FOUND
    RdmFileTimestamptokenVerifyResult.objects.filter(
        project_id=project_id,
        provider=addon_name,
        path__startswith=src_path
    ).exclude(
        inspection_result_status=api_settings.FILE_NOT_EXISTS
    ).update(inspection_result_status=tst_status)

def waterbutler_folder_file_info(pid, provider, path, node, cookies, headers):
    # get waterbutler folder file
    if provider == 'osfstorage':
        waterbutler_meta_url = waterbutler_api_url_for(
            pid, provider,
            '/' + path,
            meta=int(time.mktime(datetime.datetime.now().timetuple()))
        )
    else:
        waterbutler_meta_url = waterbutler_api_url_for(
            pid, provider,
            path,
            meta=int(time.mktime(datetime.datetime.now().timetuple()))
        )

    waterbutler_res = requests.get(waterbutler_meta_url, headers=headers, cookies=cookies)
    waterbutler_json_res = waterbutler_res.json()
    waterbutler_res.close()
    file_list = []
    child_file_list = []
    for file_data in waterbutler_json_res['data']:
        if file_data['attributes']['kind'] == 'folder':
            child_file_list.extend(waterbutler_folder_file_info(
                pid, provider, file_data['attributes']['path'],
                node, cookies, headers))
        else:
            basefile_node = BaseFileNode.resolve_class(
                provider,
                BaseFileNode.FILE
            ).get_or_create(
                node,
                file_data['attributes']['path']
            )
            basefile_node.materialized_path = file_data['attributes']['materialized']
            basefile_node.name = os.path.basename(file_data['attributes']['materialized'])
            basefile_node.save()
            if provider == 'osfstorage':
                file_info = {
                    'file_name': file_data['attributes']['name'],
                    'file_path': file_data['attributes']['materialized'],
                    'file_kind': file_data['attributes']['kind'],
                    'file_id': basefile_node._id,
                    'version': file_data['attributes']['extra']['version']
                }
            else:
                file_info = {
                    'file_name': file_data['attributes']['name'],
                    'file_path': file_data['attributes']['materialized'],
                    'file_kind': file_data['attributes']['kind'],
                    'file_id': basefile_node._id,
                    'version': ''
                }

            file_list.append(file_info)

    file_list.extend(child_file_list)
    return file_list

def userkey_generation_check(guid):
    return RdmUserKey.objects.filter(guid=Guid.objects.get(_id=guid, content_type_id=ContentType.objects.get_for_model(OSFUser).id).object_id).exists()

def userkey_generation(guid):

    try:
        generation_date = datetime.datetime.now()
        generation_date_str = generation_date.strftime('%Y%m%d%H%M%S')
        generation_date_hash = hashlib.md5(generation_date_str).hexdigest()
        generation_pvt_key_name = api_settings.KEY_NAME_FORMAT.format(
            guid, generation_date_hash, api_settings.KEY_NAME_PRIVATE, api_settings.KEY_EXTENSION)
        generation_pub_key_name = api_settings.KEY_NAME_FORMAT.format(
            guid, generation_date_hash, api_settings.KEY_NAME_PUBLIC, api_settings.KEY_EXTENSION)
        # private key generation
        pvt_key_generation_cmd = shlex.split(api_settings.SSL_PRIVATE_KEY_GENERATION.format(
            os.path.join(api_settings.KEY_SAVE_PATH, generation_pvt_key_name),
            api_settings.KEY_BIT_VALUE
        ))

        pub_key_generation_cmd = shlex.split(api_settings.SSL_PUBLIC_KEY_GENERATION.format(
            os.path.join(api_settings.KEY_SAVE_PATH, generation_pvt_key_name),
            os.path.join(api_settings.KEY_SAVE_PATH, generation_pub_key_name)
        ))

        prc = subprocess.Popen(
            pvt_key_generation_cmd, shell=False, stdin=subprocess.PIPE,
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        stdout_data, stderr_data = prc.communicate()

        prc = subprocess.Popen(
            pub_key_generation_cmd, shell=False, stdin=subprocess.PIPE,
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        stdout_data, stderr_data = prc.communicate()

        pvt_userkey_info = create_rdmuserkey_info(
            Guid.objects.get(_id=guid, content_type_id=ContentType.objects.get_for_model(OSFUser).id).object_id, generation_pvt_key_name,
            api_settings.PRIVATE_KEY_VALUE, generation_date)

        pub_userkey_info = create_rdmuserkey_info(
            Guid.objects.get(_id=guid, content_type_id=ContentType.objects.get_for_model(OSFUser).id).object_id, generation_pub_key_name,
            api_settings.PUBLIC_KEY_VALUE, generation_date)

        pvt_userkey_info.save()
        pub_userkey_info.save()

    except Exception as error:
        logger.exception(error)
        raise

def create_rdmuserkey_info(user_id, key_name, key_kind, date):
    userkey_info = RdmUserKey()
    userkey_info.guid = user_id
    userkey_info.key_name = key_name
    userkey_info.key_kind = key_kind
    userkey_info.created_time = date
    return userkey_info

def filename_formatter(file_name):
    return file_name.encode('utf-8').replace(' ', '\\ ')

class AddTimestamp:
    #1 create tsq (timestamp request) from file, and keyinfo
    def get_timestamp_request(self, file_name):
        cmd = shlex.split(api_settings.SSL_CREATE_TIMESTAMP_REQUEST.format(filename_formatter(file_name)))
        process = subprocess.Popen(
            cmd, shell=False, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        stdout_data, stderr_data = process.communicate()
        return stdout_data

    #2 send tsq to TSA, and recieve tsr (timestamp token)
    def get_timestamp_response(self, file_name, ts_request_file, key_file):
        res_content = None
        try:
            retries = Retry(
                total=api_settings.REQUEST_TIME_OUT, backoff_factor=1,
                status_forcelist=api_settings.ERROR_HTTP_STATUS)
            session = requests.Session()
            session.mount('http://', requests.adapters.HTTPAdapter(max_retries=retries))
            session.mount('https://', requests.adapters.HTTPAdapter(max_retries=retries))

            res = requests.post(
                api_settings.TIME_STAMP_AUTHORITY_URL, headers=api_settings.REQUEST_HEADER,
                data=ts_request_file, stream=True)
            res_content = res.content
            res.close()

        except Exception as ex:
            logger.exception(ex)
            traceback.print_exc()
            res_content = None

        return res_content

    def get_timestamp_upki(self, file_name, tmp_dir):
        cmd = shlex.split(api_settings.UPKI_CREATE_TIMESTAMP.format(
            filename_formatter(file_name),
            '/dev/stdout'
        ))
        try:
            process = subprocess.Popen(
                cmd, shell=False, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            stdout_data, stderr_data = process.communicate()

            return stdout_data
        except Exception as err:
            logger.exception(err)
            raise err

    def add_timestamp(self, guid, file_info, project_id, file_name, tmp_dir):
        user_id = Guid.objects.get(_id=guid, content_type_id=ContentType.objects.get_for_model(OSFUser).id).object_id

        key_file_name = RdmUserKey.objects.get(
            guid=user_id, key_kind=api_settings.PUBLIC_KEY_VALUE
        ).key_name

        try:
            if not api_settings.USE_UPKI:
                tsa_response = self.get_timestamp_response(
                    file_name, self.get_timestamp_request(file_name), key_file_name
                )
            else:
                tsa_response = self.get_timestamp_upki(file_name, tmp_dir)
        except Exception as err:
            logger.exception(err)
            tsa_response = None

        try:
            verify_data = RdmFileTimestamptokenVerifyResult.objects.get(
                file_id=file_info['file_id'])
        except RdmFileTimestamptokenVerifyResult.DoesNotExist:
            verify_data = RdmFileTimestamptokenVerifyResult()
            verify_data.file_id = file_info['file_id']
            verify_data.project_id = project_id
            verify_data.provider = file_info['provider']
            verify_data.path = file_info['file_path']
            verify_data.inspection_result_status = api_settings.TIME_STAMP_TOKEN_UNCHECKED

        verify_data.key_file_name = key_file_name
        verify_data.timestamp_token = tsa_response
        verify_data.save()

        return TimeStampTokenVerifyCheck().timestamp_check(
            guid, file_info, project_id, file_name, tmp_dir, verify_data)

class TimeStampTokenVerifyCheck:
    # get abstractNode
    def get_abstractNode(self, node_id):
        # get project name
        try:
            abstractNode = AbstractNode.objects.get(id=node_id)
        except Exception as err:
            logging.exception(err)
            abstractNode = None

        return abstractNode

    # get baseFileNode filepath
    def get_filenameStruct(self, fsnode, fname):
        if fsnode.parent is not None:
            fname = self.get_filenameStruct(fsnode.parent, fname) + '/' + fsnode.name
        else:
            fname = fsnode.name
        return fname

    def create_rdm_filetimestamptokenverify(
            self, file_id, project_id, provider, path, inspection_result_status, userid):

        userKey = RdmUserKey.objects.get(guid=userid, key_kind=api_settings.PUBLIC_KEY_VALUE)
        create_data = RdmFileTimestamptokenVerifyResult()
        create_data.file_id = file_id
        create_data.project_id = project_id
        create_data.provider = provider
        create_data.key_file_name = userKey.key_name
        create_data.path = path
        create_data.inspection_result_status = inspection_result_status
        create_data.verify_user = userid
        create_data.verify_date = timezone.now()
        return create_data

    def timestamp_check_local(self, file_info, verify_result, project_id, userid):
        """
        Check the local database for the situation of the file.

        It looks on the BaseFileNode and timestamp result table and tries
        to set the current timestamp status if something can be concluded
        from those values.
        For example, if the file has been deleted, it can set the status
        immediately.
        """
        ret = 0
        baseFileNode = None
        verify_result_title = None

        file_id = file_info['file_id']
        provider = file_info['provider']
        path = file_info['file_path']

        # get file information, verifyresult table
        if provider == 'osfstorage':
            baseFileNode = BaseFileNode.objects.get(_id=file_id)
            if baseFileNode.is_deleted and not verify_result:
                ret = api_settings.FILE_NOT_EXISTS
                verify_result_title = api_settings.FILE_NOT_EXISTS_MSG  # 'FILE missing'
                verify_result = self.create_rdm_filetimestamptokenverify(
                    file_id, project_id, provider, path, ret, userid)

            elif baseFileNode.is_deleted and verify_result:
                verify_result.inspection_result_status = api_settings.FILE_NOT_FOUND
                ret = api_settings.FILE_NOT_FOUND
                verify_result_title = api_settings.FILE_NOT_FOUND_MSG

            elif not baseFileNode.is_deleted and not verify_result:
                ret = api_settings.TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND
                verify_result_title = \
                    api_settings.TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND_MSG
                verify_result = self.create_rdm_filetimestamptokenverify(
                    file_id, project_id, provider, path, ret, userid)

            elif not baseFileNode.is_deleted and not verify_result.timestamp_token:
                verify_result.inspection_result_status = api_settings.TIME_STAMP_TOKEN_NO_DATA
                ret = api_settings.TIME_STAMP_TOKEN_NO_DATA
                verify_result_title = api_settings.TIME_STAMP_TOKEN_NO_DATA_MSG

        else:  # storage other than osfstorage:
            if not verify_result:
                ret = api_settings.TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND
                verify_result_title = api_settings.TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND_MSG
                verify_result = self.create_rdm_filetimestamptokenverify(
                    file_id, project_id, provider, path, ret, userid)

            elif not verify_result.timestamp_token:
                if verify_result.inspection_result_status != api_settings.TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND:
                    verify_result.inspection_result_status = api_settings.TIME_STAMP_TOKEN_NO_DATA
                    ret = api_settings.TIME_STAMP_TOKEN_NO_DATA
                    verify_result_title = api_settings.TIME_STAMP_TOKEN_NO_DATA_MSG
                else:
                    ret = verify_result.inspection_result_status
                    verify_result_title = api_settings.TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND_MSG

        return ret, baseFileNode, verify_result, verify_result_title

    # timestamp token check
    def timestamp_check(self, guid, file_info, project_id, file_name, tmp_dir, verify_result=None):
        logger.critical('20')
        userid = Guid.objects.get(_id=guid, content_type_id=ContentType.objects.get_for_model(OSFUser).id).object_id
        logger.critical('21')
        # get verify result
        if verify_result is None:
            logger.critical('22')
            verify_result = RdmFileTimestamptokenVerifyResult.objects.filter(
                file_id=file_info['file_id']).first()
            logger.critical('23')
        ret, baseFileNode, verify_result, verify_result_title = \
            self.timestamp_check_local(file_info, verify_result, project_id, userid)
        logger.critical('24')

        if ret == 0:
            logger.critical('25')
            if not api_settings.USE_UPKI:
                timestamptoken_file = guid + '.tsr'
                timestamptoken_file_path = os.path.join(tmp_dir, timestamptoken_file)
                with open(timestamptoken_file_path, 'wb') as fout:
                    fout.write(verify_result.timestamp_token)

                # verify timestamptoken and rootCA (FreeTSA)
                with open(timestamptoken_file_path, 'wb') as fout:
                    fout.write(verify_result.timestamp_token)

                cmd = shlex.split(api_settings.SSL_GET_TIMESTAMP_RESPONSE.format(
                    filename_formatter(file_name),
                    timestamptoken_file_path,
                    os.path.join(api_settings.KEY_SAVE_PATH, api_settings.VERIFY_ROOT_CERTIFICATE)
                ))
                # exec timestamptoken verification
                try:
                    prc = subprocess.Popen(
                        cmd, shell=False, stdin=subprocess.PIPE,
                        stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                    stdout_data, stderr_data = prc.communicate()
                    ret = api_settings.TIME_STAMP_TOKEN_UNCHECKED
                    if stdout_data.__str__().find(api_settings.OPENSSL_VERIFY_RESULT_OK) > -1:
                        ret = api_settings.TIME_STAMP_TOKEN_CHECK_SUCCESS
                        verify_result_title = api_settings.TIME_STAMP_TOKEN_CHECK_SUCCESS_MSG  # 'OK'
                    else:
                        logger.error('timestamp verification error occured.({}:{}) : {}'.format(verify_result.provider, filename_formatter(file_name), stderr_data))
                        ret = api_settings.TIME_STAMP_TOKEN_CHECK_NG
                        verify_result_title = api_settings.TIME_STAMP_TOKEN_CHECK_NG_MSG  # 'NG'
                except Exception as err:
                    logger.error('timestamp verification error occured.({}:{}) : {}'.format(verify_result.provider, filename_formatter(file_name), err))
                    ret = api_settings.TIME_STAMP_VERIFICATION_ERR
                    verify_result_title = api_settings.TIME_STAMP_VERIFICATION_ERR_MSG  # 'NG'

            else:
                #verify timestamptoken (uPKI))
                with open(file_name + '.tst', 'wb') as fout:
                    fout.write(verify_result.timestamp_token)
                cmd = shlex.split(api_settings.UPKI_VERIFY_TIMESTAMP.format(
                    filename_formatter(file_name),
                    filename_formatter(file_name) + '.tst'
                ))
                try:
                    process = subprocess.Popen(
                        cmd, shell=False, stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout_data, stderr_data = process.communicate()

                    if not stderr_data:
                        ret = api_settings.TIME_STAMP_TOKEN_CHECK_SUCCESS
                        verify_result_title = api_settings.TIME_STAMP_TOKEN_CHECK_SUCCESS_MSG  # 'OK'
                    elif stderr_data.__str__().find(api_settings.UPKI_VERIFY_INVALID_MSG) > -1:
                        ret = api_settings.TIME_STAMP_TOKEN_CHECK_NG
                        verify_result_title = api_settings.TIME_STAMP_TOKEN_CHECK_NG_MSG  # 'OK'
                    else:
                        ret = api_settings.TIME_STAMP_VERIFICATION_ERR
                        verify_result_title = api_settings.TIME_STAMP_VERIFICATION_ERR_MSG  # 'FAIL'
                        logger.error(
                            'Trusted Timestamp Token Verification failed({}/{}{}):{}'.format(project_id,
                                                                                      verify_result.provider,
                                                                                      verify_result.path,
                                                                                      stderr_data.__str__()))
                except Exception as err:
                    ret = api_settings.TIME_STAMP_VERIFICATION_ERR
                    verify_result_title = api_settings.TIME_STAMP_VERIFICATION_ERR_MSG  # 'FAIL'
                    logger.error('upki verify error({}):{}'.format(file_name.encode('utf-8'), err))

            verify_result.inspection_result_status = ret

        file_created_at = file_info.get('created')
        file_modified_at = file_info.get('modified')
        file_size = file_info.get('size')

        if not file_created_at:
            file_created_at = None
        if not file_modified_at:
            file_modified_at = None
        if not file_size:
            file_size = None

        verify_result.verify_date = timezone.now()
        verify_result.verify_user = userid
        verify_result.verify_file_created_at = file_created_at
        verify_result.verify_file_modified_at = file_modified_at
        verify_result.verify_file_size = file_size
        verify_result.save()

        # RDMINFO: TimeStampVerify
        if file_info['provider'] == 'osfstorage':
            if not baseFileNode._path:
                filename = self.get_filenameStruct(baseFileNode, '')
            else:
                filename = baseFileNode._path
            filepath = baseFileNode.provider + filename
        else:
            filepath = file_info['provider'] + file_info['file_path']

        return {
            'verify_result': ret,
            'verify_result_title': verify_result_title,
            'filepath': filepath
        }
