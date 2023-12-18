# -*- coding: utf-8 -*-

import logging
import time
import math
import xml.etree.ElementTree as ET
import base64

from owncloud import Client as NextcloudClient
from owncloud import HTTPResponseError as NCHTTPResponseError

from django.contrib.contenttypes.models import ContentType

from api.base import settings as api_settings
from framework.auth import Auth
from framework.celery_tasks import app as celery_app
from celery.contrib.abortable import AbortableTask
from osf.models import BaseFileNode, OSFUser
from osf.models.external import ExternalAccount
from osf.models.rdm_addons import RdmAddonOption
from website.util import timestamp, waterbutler
from addons.nextcloudinstitutions import apps, settings
from addons.nextcloudinstitutions.lock import TMPDIR, LOCK_PREFIX
from addons.base.lock import Lock


logger = logging.getLogger(__name__)

SHORT_NAME = apps.SHORT_NAME

ENABLE_DEBUG = False

NEXTCLOUD_FILE_UPDATE_SINCE = 'nextcloud.file_update.since'

def DEBUG(msg):
    if ENABLE_DEBUG:
        logger.error(u'DEBUG_nextcloudinstitutions: ' + msg)
    else:
        logger.debug(msg)


class FileInfo():
    def __init__(self, et):
        self.fileid = et.find('id').text
        self.ftype = et.find('type').text
        self.mtime = et.find('time').text  # upload_time (not modified time)
        self.name = et.find('name').text
        self.path = et.find('path').text
        self.muser = et.find('modified_user').text


class MetadataClient(object):
    """Nextcloud WebDAV metadata client"""

    PROPPATCH_XML_BASE = """<?xml version="1.0"?>
  <d:propertyupdate xmlns:d="DAV:" xmlns:nc="http://nextcloud.org/ns">
  <d:set>
    <d:prop>
      {}
    </d:prop>
  </d:set>
</d:propertyupdate>"""

    PROPFIND_XML_BASE = """<?xml version="1.0" encoding="UTF-8"?>
  <d:propfind xmlns:d="DAV:" xmlns:nc="http://nextcloud.org/ns" >
  <d:prop xmlns:oc="http://owncloud.org/ns">
    {}
  </d:prop>
</d:propfind>"""

    def __init__(self, server, account, password):
        self.account = account
        self.password = password
        self.server = server
        self.client = NextcloudClient(self.server, dav_endpoint_version=2)
        self.client.login(self.account, self.password)

    def set_metadata(self, path, attributes):
        array = []
        for k, v in attributes.items():
            array.append('<nc:' + k + '>' + v + '</nc:' + k + '>')
        str_attributes = '    '.join(array)
        xml = self.PROPPATCH_XML_BASE.format(str_attributes)
        try:
            res = self.client._make_dav_request('PROPPATCH', path, data=xml)
        except NCHTTPResponseError:
            logger.error(u'cannot set timestamp: user={}, path={}'.format(self.account, path))
            return None
        return res

    def get_metadata(self, path, attributes):
        array = []
        for a in attributes:
            array.append('<nc:' + a + '/>')
        str_attributes = '    '.join(array)
        xml = self.PROPFIND_XML_BASE.format(str_attributes)
        try:
            res = self.client._make_dav_request('PROPFIND', path, data=xml)
        except NCHTTPResponseError:
            logger.error(u'cannot get timestamp: user={}, path={}'.format(self.account, path))
            return None
        return res

    def get_attribute(self, fileinfo, prop):
        key = '{http://nextcloud.org/ns}' + prop
        return fileinfo.attributes[key]


def get_timestamp(node_settings, path):
    DEBUG(u'get_timestamp: path={}'.format(path))
    provider = node_settings.provider
    external_account = provider.account
    url, username = external_account.provider_id.rsplit(':', 1)
    password = external_account.oauth_key
    attributes = [
        settings.PROPERTY_KEY_TIMESTAMP,
        settings.PROPERTY_KEY_TIMESTAMP_STATUS
    ]
    cli = MetadataClient(url, username, password)
    res = cli.get_metadata(path, attributes)
    if res is not None:
        timestamp = cli.get_attribute(res[0], settings.PROPERTY_KEY_TIMESTAMP)
        if timestamp is None:
            decoded_timestamp = None
        else:
            decoded_timestamp = base64.b64decode(timestamp)
        # DEBUG(u'get timestamp: {}'.format(timestamp))
        timestamp_status = cli.get_attribute(res[0], settings.PROPERTY_KEY_TIMESTAMP_STATUS)
        try:
            timestamp_status = int(timestamp_status)
        except Exception:
            timestamp_status = None
        DEBUG(u'get timestamp_status: {}'.format(timestamp_status))
        context = {}
        context['url'] = url
        context['username'] = username
        context['password'] = password
        return (decoded_timestamp, timestamp_status, context)
    return (None, None, None)


def set_timestamp(node_settings, path, timestamp_data, timestamp_status, context=None):
    DEBUG(u'set_timestamp: path={}'.format(path))
    if context is None:
        provider = node_settings.provider
        external_account = provider.account
        url, username = external_account.provider_id.rsplit(':', 1)
        password = external_account.oauth_key
    else:
        url = context['url']
        username = context['username']
        password = context['password']
    encoded_timestamp = base64.b64encode(timestamp_data)
    # DEBUG(u'set timestamp: {}'.format(encoded_timestamp))
    attributes = {
        settings.PROPERTY_KEY_TIMESTAMP: encoded_timestamp,
        settings.PROPERTY_KEY_TIMESTAMP_STATUS: str(timestamp_status)
    }
    cli = MetadataClient(url, username, password)
    res = cli.set_metadata(path, attributes)
    if res:
        DEBUG(u'metadata res: {}'.format(type(res)))


def _list_updated_files(externa_account, since):
    url, username = externa_account.provider_id.rsplit(':', 1)
    password = externa_account.oauth_key

    client = NextcloudClient(url + '/')
    client.login(username, password)
    response = client.make_ocs_request(
        'GET',
        'apps/file_upload_notification',
        'api/recent?since={}'.format(since))

    root = ET.fromstring(response.content)
    meta = root[0]
    status = meta[0]
    statuscode = meta[1]
    DEBUG(u'status: {}, code: {}'.format(status.text, statuscode.text))
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
            DEBUG(u'selected user for timestamp: username={}, eppn={}'.format(user.username, user.eppn))
            return user
    raise Exception('unexpected condition')


def _check_for_file(project, path, fileinfo):
    node = project.owner
    if node.is_deleted:
        return
    admin = _select_admin(node)
    admin_cookie = admin.get_or_create_cookie().decode()
    created = True

    cls = BaseFileNode.resolve_class(SHORT_NAME, BaseFileNode.FILE)
    if _file_exists(cls, node, path):
        created = False
    file_node = cls.get_or_create(node, path)
    json = waterbutler.get_node_info(admin_cookie, node._id, SHORT_NAME, path)
    if json is None:
        DEBUG(u'waterbutler.get_node_info() is None: path={}'.format(path))
        return

    data = json.get('data')
    if data is None:
        DEBUG('waterbutler.get_node_info().get("data") is None: path={}'.format(path))
        return
    DEBUG(u'data: {}'.format(str(data)))

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
    DEBUG(u'check timestamp: verify_result={}'.format(verify_result.get('verify_result_title')))
    if verify_result['verify_result'] == api_settings.TIME_STAMP_TOKEN_CHECK_SUCCESS:
        return  # already checked

    # The file is created (new file) or modified.
    user = None
    if fileinfo.muser:
        osfuser_guid = project.extuser_to_osfuser(fileinfo.muser)
        DEBUG(u'osfuser_guid: {}'.format(osfuser_guid))
        if osfuser_guid:
            try:
                user = OSFUser.objects.get(guids___id=osfuser_guid)
                DEBUG(u'user: {}'.format(str(user)))
            except OSFUser.DoesNotExist:
                logger.warning(u'modified by unknown user: email={}'.format(fileinfo.muser))

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
    logger.info(u'update timestamp by Webhook for Nextcloud: node_guid={}, path={}, verify_result={}'.format(
        node._id, path, verify_result.get('verify_result_title')))


def _check_project_files(addon_option, fileinfo):
    from addons.nextcloudinstitutions.models import NodeSettings

    for project in NodeSettings.objects.filter(addon_option=addon_option):
        path = project.root_folder_fullpath
        if fileinfo.path.startswith(path):
            internal_path = fileinfo.path[len(path):]
            if internal_path:
                DEBUG(u'internal_path: {}'.format(internal_path))
                _check_for_file(project, internal_path, fileinfo)


@celery_app.task(bind=True, base=AbortableTask)
def celery_check_updated_files(self, provider_id, since, interval):
    DEBUG(u'provider_id: {}, since: {}, interval: {}'.format(provider_id, since, interval))

    start_time = time.time()
    DEBUG(u'start_time: {}'.format(start_time))

    # to wait for updating timestamp in create_waterbutler_log()
    time.sleep(5)

    ea = ExternalAccount.objects.get(
        provider=SHORT_NAME, provider_id=provider_id)
    DEBUG(u'external account id: {}'.format(ea._id))

    lock = Lock(TMPDIR, LOCK_PREFIX, ea._id)
    if not lock.trylock():
        DEBUG(u'lock acquisition failed')
        return  # exit

    opt = RdmAddonOption.objects.get(
        provider=SHORT_NAME, external_accounts=ea)
    if opt.extended is None:
        opt.extended = {}

    val = opt.extended.get(NEXTCLOUD_FILE_UPDATE_SINCE)
    if val and val.isdigit():
        DEBUG(u'get "since" from DB: {}'.format(val))
        since = val

    updated_files = _list_updated_files(ea, since)
    DEBUG(u'update files: {}'.format(str(updated_files)))

    latest = since
    for f in updated_files:
        DEBUG(u'path: {}, mtime: {}, modified user: {}'.format(f.path, f.mtime, f.muser))
        if f.ftype == 'file':
            try:
                _check_project_files(opt, f)
                if latest < f.mtime:
                    latest = f.mtime
                    DEBUG(u'latest: {}'.format(str(latest)))
            except Exception:
                logger.exception(u'Insititution={}, Nextcloud ID={}'.format(opt.institution, provider_id))

    # wait for the specified interval
    current_time = time.time()
    recheck_time = start_time + float(interval)
    sleep_time = 0
    if recheck_time - current_time > 0:
        sleep_time = math.ceil(recheck_time - current_time)
        time.sleep(sleep_time)
    DEBUG(u'current: {}, recheck: {}, sleep: {}'.format(current_time, recheck_time, sleep_time))

    updated_files2 = _list_updated_files(ea, latest)
    DEBUG(u'update files2: {}'.format(str(updated_files2)))

    for f in updated_files2:
        DEBUG(u'path: {}, mtime: {}, modified user: {}'.format(f.path, f.mtime, f.muser))
        if f.ftype == 'file':
            try:
                _check_project_files(opt, f)
                if latest < f.mtime:
                    latest = f.mtime
                    DEBUG(u'latest: {}'.format(str(latest)))
            except Exception:
                logger.exception(u'Insititution={}, Nextcloud ID={}'.format(opt.institution, provider_id))

    opt.extended[NEXTCLOUD_FILE_UPDATE_SINCE] = latest
    opt.save()
    lock.unlock()
