# -*- coding: utf-8 -*-

import logging
import time
import math
import xml.etree.ElementTree as ET

from owncloud import Client as NextcloudClient

from django.contrib.contenttypes.models import ContentType

from api.base import settings as api_settings
from framework.auth import Auth
from framework.celery_tasks import app as celery_app
from celery.contrib.abortable import AbortableTask
from osf.models import BaseFileNode, OSFUser
from osf.models.external import ExternalAccount
from osf.models.rdm_addons import RdmAddonOption
from website.util import timestamp, waterbutler
from addons.nextcloudinstitutions import apps, lock


logger = logging.getLogger(__name__)

SHORT_NAME = apps.SHORT_NAME

ENABLE_DEBUG = False

def DEBUG(msg):
    if ENABLE_DEBUG:
        logger.error(u'DEBUG_nextcloudinstitutions: ' + msg)
    else:
        logger.debug(msg)


class FileInfo():
    def __init__(self, et):
        self.fileid = et.find('id').text
        self.ftype = et.find('type').text
        self.mtime = et.find('mtime').text
        self.name = et.find('name').text
        self.path = et.find('path').text
        self.muser = et.find('modified_user').text


def _list_updated_files(externa_account, since):
    url, username = externa_account.provider_id.rsplit(':', 1)
    password = externa_account.oauth_key

    client = NextcloudClient(url + '/')
    client.login(username, password)
    response = client.make_ocs_request(
        'GET',
        'apps/file-update-notifications',
        'api/recent?since={}'.format(since))

    root = ET.fromstring(response.content)
    meta = root[0]
    status = meta[0]
    statuscode = meta[1]
    DEBUG('status: {}, code: {}'.format(status.text, statuscode.text))
    OCSAPI_SUCCESS = '100'
    if statuscode.text != OCSAPI_SUCCESS:
        return None

    data = root[1]
    files = data[1]
    updated_files = []
    for f in files:
        fi = FileInfo(f)
        updated_files.append(fi)

    return updated_files


def _file_exists(cls, target, path):
    # see osf.models.files/BaseFileNode.get_or_create()
    content_type = ContentType.objects.get_for_model(target)
    kwargs = {'target_object_id': target.id,
              'target_content_type': content_type,
              '_path': '/' + path.lstrip('/')}
    return cls.objects.filter(**kwargs).exists()


def _select_admin(node):
    # select from admin contributors
    for user in node.contributors.all():
        if user.is_disabled or user.eppn is None:
            continue
        if node.is_admin_contributor(user):
            DEBUG('selected user for timestamp: username={}, eppn={}'.format(user.username, user.eppn))
            return user
    raise Exception('unexpected condition')


def _check_for_file(project, path, fileinfo):
    node = project.owner
    admin = _select_admin(node)
    admin_cookie = admin.get_or_create_cookie()
    created = True

    cls = BaseFileNode.resolve_class(SHORT_NAME, BaseFileNode.FILE)
    if _file_exists(cls, node, path):
        created = False
    file_node = cls.get_or_create(node, path)
    json = waterbutler.get_node_info(admin_cookie, node._id, SHORT_NAME, path)
    if json is None:
        DEBUG('waterbutler.get_node_info() is None: path={}'.format(path))
        return

    data = json.get('data')
    if data is None:
        DEBUG('waterbutler.get_node_info().get("data") is None: path={}'.format(path))
        return
    DEBUG('data: {}'.format(str(data)))

    attrs = data['attributes']
    file_node.update(None, attrs, user=admin)  # update content_hash
    info = {
        'file_id': file_node._id,
        'file_name': attrs.get('name'),
        'file_path': attrs.get('materialized'),
        'size': attrs.get('size'),
        'created': attrs.get('created_utc'),
        'modified': attrs.get('modified_utc'),
        'file_version': '',
        'provider': SHORT_NAME
    }
    # verified by admin
    verify_result = timestamp.check_file_timestamp(admin.id, node, info, verify_external_only=True)
    DEBUG('check timestamp: verify_result={}'.format(verify_result.get('verify_result_title')))
    if verify_result['verify_result'] == api_settings.TIME_STAMP_TOKEN_CHECK_SUCCESS:
        return  # already checked

    # The file is created (new file) or modified.
    user = None
    if fileinfo.muser:
        osfuser_guid = project.extuser_to_osfuser(fileinfo.muser)
        DEBUG('osfuser_guid: {}'.format(osfuser_guid))
        if osfuser_guid:
            try:
                user = OSFUser.objects.get(guids___id=osfuser_guid)
                DEBUG('user: {}'.format(str(user)))
            except OSFUser.DoesNotExist:
                logger.warning('modified by unknown user: email={}'.format(fileinfo.muser))

    metadata = {
        'path': path,
        'materialized': path,
    }
    if created:
        action = 'file_added'
    else:
        action = 'file_updated'
    if user:  # modified by user
        verify_result = timestamp.add_token(user.id, node, info)
        project.create_waterbutler_log(Auth(user), action, metadata)
    else:  # modified by unknown user
        verify_result = timestamp.add_token(admin.id, node, info)
        project.create_waterbutler_log(None, action, metadata)
    logger.info('update timestamp by Webhook for Nextcloud: node_guid={}, path={}, verify_result={}'.format(
        node._id, path, verify_result.get('verify_result_title')))


def _check_project_files(addon_option, fileinfo):
    from addons.nextcloudinstitutions.models import NodeSettings

    for project in NodeSettings.objects.filter(addon_option=addon_option):
        project_name = project.folder_id.split('/')[-1]
        if project_name in fileinfo.path:
            internal_path = fileinfo.path.split(project_name)[-1]
            DEBUG('internal_path: {}'.format(internal_path))
            _check_for_file(project, internal_path, fileinfo)


@celery_app.task(bind=True, base=AbortableTask)
def celery_check_updated_files(self, provider_id, since, interval):
    DEBUG('provider_id: {}, since: {}, interval: {}'.format(provider_id, since, interval))
    if not lock.LOCK_RUN.trylock():
        DEBUG('lock acquisition failed')
        return  # exit

    start_time = time.time()
    DEBUG('start_time: {}'.format(start_time))

    ea = ExternalAccount.objects.get(
        provider=SHORT_NAME, provider_id=provider_id)
    opt = RdmAddonOption.objects.get(
        provider=SHORT_NAME, external_accounts=ea)
    if opt.extended is None:
        opt.extended = {}

    updated_files = _list_updated_files(ea, since)
    DEBUG('update files: {}'.format(str(updated_files)))

    latest = since
    for f in updated_files:
        DEBUG('path: {}, mtime: {}, modified user: {}'.format(f.path, f.mtime, f.muser))
        if f.ftype == 'file':
            try:
                _check_project_files(opt, f)
                if latest < f.mtime:
                    latest = f.mtime
                    DEBUG('latest: {}'.format(str(latest)))
            except Exception:
                logger.exception('Insititution={}, Nextcloud ID={}'.format(opt.institution, provider_id))

    # wait for the specified interval
    current_time = time.time()
    recheck_time = start_time + float(interval)
    sleep_time = 0
    if recheck_time - current_time > 0:
        sleep_time = math.ceil(recheck_time - current_time)
        time.sleep(sleep_time)
    DEBUG('current: {}, recheck: {}, sleep: {}'.format(current_time, recheck_time, sleep_time))

    updated_files2 = _list_updated_files(ea, latest)
    DEBUG('update files2: {}'.format(str(updated_files2)))

    for f in updated_files2:
        DEBUG('path: {}, mtime: {}, modified user: {}'.format(f.path, f.mtime, f.muser))
        if f.ftype == 'file':
            try:
                _check_project_files(opt, f)
            except Exception:
                logger.exception('Insititution={}, Nextcloud ID={}'.format(opt.institution, provider_id))

    lock.LOCK_RUN.unlock()
