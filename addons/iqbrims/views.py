# -*- coding: utf-8 -*-
from datetime import datetime
from functools import reduce
from rest_framework import status as http_status
import json
import logging
from urllib.parse import quote

from django.db import transaction
from django.db.models import Subquery
from flask import request

from addons.iqbrims.client import (
    IQBRIMSClient,
    IQBRIMSFlowableClient,
    SpreadsheetClient,
    IQBRIMSWorkflowUserSettings
)
from framework.auth import Auth
from website.mails import Mail, send_mail
from framework.exceptions import HTTPError

from osf.models import (BaseFileNode, RdmAddonOption)
from website.project.decorators import (
    must_have_addon,
    must_be_valid_project,
    must_be_addon_authorizer,
    must_have_permission,
    must_be_contributor,
)
from website import settings as website_settings
from website.ember_osf_web.views import use_ember_app
from addons.iqbrims import settings

from addons.base import generic_views, exceptions
from addons.iqbrims.serializer import IQBRIMSSerializer
from addons.iqbrims.models import NodeSettings as IQBRIMSNodeSettings
from addons.iqbrims.models import REVIEW_FOLDERS, REVIEW_FILE_LIST
from addons.iqbrims.utils import (
    must_have_valid_hash,
    get_folder_title,
    add_comment,
    to_comment_string,
    validate_file_list,
    embed_variables,
)

logger = logging.getLogger(__name__)

SHORT_NAME = 'iqbrims'
FULL_NAME = 'IQB-RIMS'


iqbrims_account_list = generic_views.account_list(
    SHORT_NAME,
    IQBRIMSSerializer
)

iqbrims_get_config = generic_views.get_config(
    SHORT_NAME,
    IQBRIMSSerializer
)

def _set_folder(node_addon, folder, auth):
    node_addon.set_folder(folder, auth=auth)
    node_addon.save()

iqbrims_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    IQBRIMSSerializer,
    _set_folder
)

iqbrims_import_auth = generic_views.import_auth(
    SHORT_NAME,
    IQBRIMSSerializer
)

iqbrims_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

@must_be_valid_project
@must_be_contributor
@must_have_addon('iqbrims', 'node')
def project_iqbrims(**kwargs):
    node = kwargs['node'] or kwargs['project']
    iqbrims = node.get_addon('iqbrims')
    status = iqbrims.get_status()
    edit = request.args.get('edit', None)
    if edit is not None and 'edit' not in status:
        _iqbrims_set_status(node, {'edit': edit})
    return use_ember_app()

@must_have_addon(SHORT_NAME, 'node')
@must_have_permission('write')
@must_be_addon_authorizer(SHORT_NAME)
def iqbrims_folder_list(node_addon, **kwargs):
    """ Returns all the subsequent folders under the folder id passed.
        Not easily generalizable due to `path` kwarg.
    """
    path = request.args.get('path', '')
    folder_id = request.args.get('folder_id', 'root')

    return node_addon.get_folders(folder_path=path, folder_id=folder_id)

@must_be_valid_project
@must_have_permission('read')
@must_have_addon(SHORT_NAME, 'node')
def iqbrims_get_status(**kwargs):
    node = kwargs['node'] or kwargs['project']
    iqbrims = node.get_addon('iqbrims')
    management_node = _get_management_node(node)
    management_node_addon = IQBRIMSNodeSettings.objects.get(owner=management_node)
    if management_node_addon is None:
        logger.error('management_node is not set.')
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, 'IQB-RIMS addon disabled in management node')
    logger.debug('checking management_node...')
    try:
        access_token = management_node_addon.fetch_access_token()
    except exceptions.InvalidAuthError:
        logger.error('fetch_access_token is failed.')
        raise HTTPError(403)
    logger.debug('management_node has been configured.')
    user_settings = IQBRIMSWorkflowUserSettings(access_token, management_node_addon.folder_id)
    status = iqbrims.get_status()
    logger.debug('extracting settings from management_node...')
    status['labo_list'] = [u'{}:{}'.format(l['id'], l['text'])
                           for l in user_settings.LABO_LIST]
    status['review_folders'] = REVIEW_FOLDERS
    is_admin = management_node._id == node._id
    status['is_admin'] = is_admin
    if is_admin:
        status['task_url'] = user_settings.FLOWABLE_TASK_URL
    client = IQBRIMSClient(access_token)
    if iqbrims.folder_id is not None:
        status.update(_iqbrims_get_drive_url(client, iqbrims.folder_id, status))
    logger.debug('settings extracted.')
    return {'data': {'id': node._id, 'type': 'iqbrims-status',
                     'attributes': status}}

@must_be_valid_project
@must_have_permission('write')
@must_have_addon(SHORT_NAME, 'node')
def iqbrims_set_status(**kwargs):
    node = kwargs['node'] or kwargs['project']
    try:
        status = request.json['data']['attributes']
    except KeyError:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    auth = kwargs['auth']
    rstatus = _iqbrims_set_status(node, status, auth)
    return {'data': {'id': node._id, 'type': 'iqbrims-status',
                     'attributes': rstatus}}

@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
@must_have_valid_hash()
def iqbrims_post_notify(**kwargs):
    node = kwargs['node'] or kwargs['project']
    logger.info('Notified: {}'.format(request.data))
    data = json.loads(request.data)
    notify_type = data['notify_type']
    notify_title = data['notify_title'] if 'notify_title' in data else None
    notify_body = data['notify_body'] if 'notify_body' in data else None
    notify_body_md = data['notify_body_md'] \
                     if 'notify_body_md' in data else None
    use_mail = data['use_mail'] if 'use_mail' in data else False
    node_comments = []
    node_emails = []
    mgmtnode = _get_management_node(node)
    admin_emails = reduce(lambda x, y: x + y,
                          [[e.address for e in u.emails.all()]
                           for u in mgmtnode.contributors])
    if 'to' in data:
        to = data['to']
        if 'user' in to:
            node_comments.append(node)
            node_emails.append((node, admin_emails, 'iqbrims_user'))
        if 'admin' in to:
            node_comments.append(mgmtnode)
            node_emails.append((mgmtnode, None, 'iqbrims_management'))
    else:
        if 'comment_to' in data:
            to = data['comment_to']
            if 'user' in to:
                node_comments.append(node)
            if 'admin' in to:
                node_comments.append(mgmtnode)
        if 'email_to' in data:
            to = data['email_to']
            if 'user' in to:
                node_emails.append((node, admin_emails, 'iqbrims_user'))
            if 'admin' in to:
                node_emails.append((mgmtnode, None, 'iqbrims_management'))
    action = 'iqbrims_{}'.format(notify_type)
    if notify_body is None:
        if action in settings.LOG_MESSAGES:
            notify_body = settings.LOG_MESSAGES[action]
            href_prefix = website_settings.DOMAIN.rstrip('/') + '/'
            href = href_prefix + node.creator._id + '/'
            uname = 'User <a href="{1}">{0}</a>'.format(node.creator.username,
                                                        href)
            notify_body = notify_body.replace('${user}', uname)
            href = href_prefix + node._id + '/'
            nname = 'Paper <a href="{1}">{0}</a>'.format(node.title, href)
            notify_body = notify_body.replace('${node}', nname)
    if notify_body_md is None:
        notify_body_md = to_comment_string(notify_body) if notify_body is not None else ''
    if notify_title is None:
        notify_title = action
    if action in settings.LOG_MESSAGES:
        for n in [node, mgmtnode]:
            n.add_log(
                action=action,
                params={
                    'project': n.parent_id,
                    'node': node._id,
                },
                auth=Auth(user=node.creator),
            )
    for n in node_comments:
        add_comment(node=n, user=n.creator, title=notify_title, body=notify_body_md)
    for n, cc_addrs, email_template in node_emails:
        if not use_mail or len(n.contributors) == 0:
            continue
        emails = reduce(lambda x, y: x + y,
                        [[e.address for e in u.emails.all()]
                         for u in n.contributors])
        send_mail(','.join(emails), Mail(email_template, notify_title),
                  cc_addr=','.join(cc_addrs) if cc_addrs is not None else None,
                  replyto=cc_addrs[0] if cc_addrs is not None else None,
                  title=n.title, guid=n._id, author=node.creator,
                  notify_type=notify_type, mimetype='html',
                  notify_body=notify_body, notify_title=notify_title)
    return {'status': 'complete'}

@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
@must_have_valid_hash()
def iqbrims_post_workflow_state(**kwargs):
    node = kwargs['node'] or kwargs['project']
    part = kwargs['part']
    logger.info('Workflow State: {}, {}'.format(part, request.data))
    reqdata = json.loads(request.data)
    status = {}
    status['workflow_' + part + '_state'] = reqdata['state']
    status['workflow_' + part + '_permissions'] = reqdata['permissions']
    if 'updated' in reqdata:
        status['workflow_' + part + '_updated'] = reqdata['updated']
    if 'status' in reqdata:
        for k, v in reqdata['status'].items():
            status[k] = v
    rstatus = _iqbrims_set_status(node, status)
    return {'status': 'complete', 'data': rstatus}

@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
@must_have_valid_hash()
def iqbrims_get_storage(**kwargs):
    node = kwargs['node'] or kwargs['project']
    iqbrims = node.get_addon('iqbrims')
    folder = kwargs['folder']
    folder_name = None
    sub_folder_name = None
    file_name = None
    validate = None
    urls_for_all_files = False
    if folder == 'index':
        folder_name = REVIEW_FOLDERS['raw']
        file_name = settings.INDEXSHEET_FILENAME
        validate = _iqbrims_filled_index
    elif folder == 'imagelist':
        folder_name = REVIEW_FOLDERS['paper']
        sub_folder_name = settings.IMAGELIST_FOLDERNAME
        file_name = settings.IMAGELIST_FILENAME
        urls_for_all_files = True
    else:
        folder_name = REVIEW_FOLDERS[folder]
        file_name = REVIEW_FILE_LIST
        urls_for_all_files = True
    try:
        access_token = iqbrims.fetch_access_token()
    except exceptions.InvalidAuthError:
        raise HTTPError(403)
    client = IQBRIMSClient(access_token)
    folders = client.folders(folder_id=iqbrims.folder_id)
    folders = [f for f in folders if f['title'] == folder_name]
    assert len(folders) > 0
    sub_folders = None
    if sub_folder_name is not None:
        sub_folders = client.folders(folder_id=folders[0]['id'])
        sub_folders = [f for f in sub_folders if f['title'] == sub_folder_name]
        if len(sub_folders) == 0:
            return {'status': 'processing', 'comment': ''}
    logger.info(u'Checking Storage: {}, {}, {}'.format(folder, folder_name,
                                                       folders[0]['id']))
    all_files = client.files(folder_id=folders[0]['id'])
    files = all_files

    management_node = _get_management_node(node)
    management_node_addon = IQBRIMSNodeSettings.objects.get(owner=management_node)
    if management_node_addon is None:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, 'IQB-RIMS addon disabled in management node')
    user_settings = IQBRIMSWorkflowUserSettings(access_token, management_node_addon.folder_id)

    logger.debug(u'Result files: {}'.format([f['title'] for f in files]))
    if file_name is not None:
        files = [f for f in files
                 if f['title'] == file_name and (validate is None or validate(user_settings, access_token, f))]
    if len(files) > 0 and file_name == REVIEW_FILE_LIST:
        files = files if validate_file_list(client, files[0], all_files) else []
    folder_path = iqbrims.folder_path
    base_folder_path = management_node.get_addon('googledrive').folder_path
    assert folder_path.startswith(base_folder_path)
    root_folder_path = folder_path[len(base_folder_path):]
    logger.debug(u'Folder path: {}'.format(root_folder_path))
    node_urls = []
    management_urls = []
    url_files = all_files if urls_for_all_files else files
    for f in url_files:
        url_folder_path = folders[0]['title']
        with transaction.atomic():
            path = u'{}/{}'.format(url_folder_path, f['title'])
            path = quote(path.encode('utf8'))
            logger.info(u'Node URL: {}'.format(path))
            file_node = BaseFileNode.resolve_class('iqbrims', BaseFileNode.FILE).get_or_create(node, path)
            url = website_settings.DOMAIN.rstrip('/') + '/' + file_node.get_guid(create=True)._id + '/'
            node_urls.append({'title': f['title'], 'url': url, 'path': path})
        with transaction.atomic():
            sroot_folder_path = root_folder_path.strip('/')
            path = u'{}/{}/{}'.format(sroot_folder_path, url_folder_path, f['title'])
            path = quote(path.encode('utf8'))
            logger.info(u'Management URL: {}'.format(path))
            file_node = BaseFileNode.resolve_class('googledrive', BaseFileNode.FILE).get_or_create(management_node, path)
            url = website_settings.DOMAIN.rstrip('/') + '/' + file_node.get_guid(create=True)._id + '/'
            mfr_url = website_settings.MFR_SERVER_URL.rstrip('/') + '/export?url=' + url
            drive_url = f['alternateLink'] if 'alternateLink' in f else None
            management_urls.append({'title': f['title'],
                                    'path': path,
                                    'url': url,
                                    'mfr_url': mfr_url,
                                    'drive_url': drive_url})
    logger.info('Urls: node={}, management={}'.format(node_urls, management_urls))
    status = iqbrims.get_status()
    comment_key = folder + '_comment'
    comment = status[comment_key] if comment_key in status else ''
    alt_folders = sub_folders if sub_folders is not None else folders
    folder_drive_url = alt_folders[0]['alternateLink'] \
                       if len(alt_folders) > 0 and 'alternateLink' in alt_folders[0] \
                       else None

    return {'status': 'complete' if len(files) > 0 else 'processing',
            'root_folder': root_folder_path,
            'folder_drive_url': folder_drive_url,
            'urls': node_urls,
            'whole': status,
            'comment': comment,
            'management': {'id': management_node._id,
                           'urls': management_urls}}

@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
@must_have_valid_hash()
def iqbrims_reject_storage(**kwargs):
    node = kwargs['node'] or kwargs['project']
    iqbrims = node.get_addon('iqbrims')
    folder = kwargs['folder']
    try:
        access_token = iqbrims.fetch_access_token()
    except exceptions.InvalidAuthError:
        raise HTTPError(403)

    management_node = _get_management_node(node)
    management_node_addon = IQBRIMSNodeSettings.objects.get(owner=management_node)
    if management_node_addon is None:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, 'IQB-RIMS addon disabled in management node')
    user_settings = IQBRIMSWorkflowUserSettings(access_token, management_node_addon.folder_id)

    client = IQBRIMSClient(access_token)
    folder_name = None
    file_name = None
    reject = lambda f: client.delete_file(f['id'])
    if folder == 'index':
        folder_name = REVIEW_FOLDERS['raw']
        file_name = settings.INDEXSHEET_FILENAME
        reject = lambda f: _iqbrims_reset_index(user_settings, access_token, f)
    else:
        folder_name = REVIEW_FOLDERS[folder]
    folders = client.folders(folder_id=iqbrims.folder_id)
    folders = [f for f in folders if f['title'] == folder_name]
    if len(folders) > 0:
        files = client.files(folder_id=folders[0]['id'])
    else:
        files = []
    files = [f for f in files if file_name is None or f['title'] == file_name]

    folder_path = iqbrims.folder_path
    base_folder_path = management_node.get_addon('googledrive').folder_path
    assert folder_path.startswith(base_folder_path)
    root_folder_path = folder_path[len(base_folder_path):]

    if file_name is not None:
        if len(files) == 0:
            logger.info(u'Already rejected: {}, {}'.format(folder,
                                                           file_name))
            return {'status': 'nochange',
                    'root_folder': root_folder_path}
        logger.info(u'Rejecting Storage: {}, {}, {}'.format(folder,
                                                            file_name,
                                                            files[0]['id']))
        reject(files[0])
        return {'status': 'rejected',
                'root_folder': root_folder_path}
    else:
        if len(folders) == 0:
            logger.info(u'Already rejected: {}, {}'.format(folder,
                                                           folder_name))
            return {'status': 'nochange',
                    'root_folder': root_folder_path}
        logger.info(u'Rejecting Storage: {}, {}, {}'.format(folder,
                                                            folder_name,
                                                            folders[0]['id']))
        dtid = datetime.now().strftime('%Y%m%d-%H%M%S')
        rejected_name = u'{}.{}'.format(folder_name, dtid)
        client.rename_folder(folders[0]['id'], rejected_name)
        client.create_folder(iqbrims.folder_id, folder_name)
        node_urls = []
        management_urls = []
        for f in files:
            url = website_settings.DOMAIN.rstrip('/') + '/' + node._id + \
                '/files/iqbrims/' + \
                quote(rejected_name.encode('utf8')) + '/' + \
                quote(f['title'].encode('utf8'))
            node_urls.append({'title': f['title'], 'url': url})
            url = website_settings.DOMAIN.rstrip('/') + '/' + management_node._id + \
                  '/files/googledrive' + \
                  quote(root_folder_path.encode('utf8')) + \
                  quote(rejected_name.encode('utf8')) + '/' + \
                  quote(f['title'].encode('utf8'))
            management_urls.append({'title': f['title'], 'url': url})
        return {'status': 'rejected',
                'root_folder': root_folder_path,
                'urls': node_urls,
                'management': {'id': management_node._id,
                               'urls': management_urls}}

@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
@must_have_valid_hash()
def iqbrims_create_index(**kwargs):
    node = kwargs['node'] or kwargs['project']
    iqbrims = node.get_addon('iqbrims')
    folder_name = REVIEW_FOLDERS['raw']
    try:
        access_token = iqbrims.fetch_access_token()
    except exceptions.InvalidAuthError:
        raise HTTPError(403)
    management_node = _get_management_node(node)
    management_node_addon = IQBRIMSNodeSettings.objects.get(owner=management_node)
    if management_node_addon is None:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, 'IQB-RIMS addon disabled in management node')
    user_settings = IQBRIMSWorkflowUserSettings(access_token, management_node_addon.folder_id)

    client = IQBRIMSClient(access_token)
    folders = client.folders(folder_id=iqbrims.folder_id)
    folders = [f for f in folders if f['title'] == folder_name]
    assert len(folders) > 0
    files = client.files(folder_id=folders[0]['id'])
    files = [f for f in files if f['title'] == 'files.txt']
    logger.debug(u'Result files: {}'.format([f['title'] for f in files]))
    if len(files) == 0:
        return {'status': 'processing'}
    files = client.get_content(files[0]['id']).decode('utf8').split('\n')
    if user_settings.FLOWABLE_DATALIST_TEMPLATE_ID is None:
        _, r = client.create_spreadsheet_if_not_exists(folders[0]['id'],
                                                       settings.INDEXSHEET_FILENAME)
    else:
        _, r = client.copy_file_if_not_exists(user_settings.FLOWABLE_DATALIST_TEMPLATE_ID,
                                              folders[0]['id'],
                                              settings.INDEXSHEET_FILENAME)
    sclient = SpreadsheetClient(r['id'], access_token)
    all_sheets = sclient.sheets()
    files_sheets = [s
                    for s in all_sheets
                    if s['properties']['title'] == user_settings.INDEXSHEET_FILES_SHEET_NAME]
    mgmt_sheets = [s
                   for s in all_sheets
                   if s['properties']['title'] == user_settings.INDEXSHEET_MANAGEMENT_SHEET_NAME]
    logger.info('Spreadsheet: id={}, sheet={}'.format(r['id'], files_sheets))
    added = False
    if len(mgmt_sheets) == 0:
        sclient.add_sheet(user_settings.INDEXSHEET_MANAGEMENT_SHEET_NAME)
        added = True
    if len(files_sheets) == 0 and user_settings.INDEXSHEET_MANAGEMENT_SHEET_NAME != user_settings.INDEXSHEET_FILES_SHEET_NAME:
        sclient.add_sheet(user_settings.INDEXSHEET_FILES_SHEET_NAME)
        added = True
    if added:
        all_sheets = sclient.sheets()
        files_sheets = [s
                        for s in all_sheets
                        if s['properties']['title'] == user_settings.INDEXSHEET_FILES_SHEET_NAME]
        mgmt_sheets = [s
                       for s in all_sheets
                       if s['properties']['title'] == user_settings.INDEXSHEET_MANAGEMENT_SHEET_NAME]
    assert len(files_sheets) == 1 and len(mgmt_sheets) == 1
    files_sheet_id = files_sheets[0]['properties']['title']
    mgmt_sheet_id = mgmt_sheets[0]['properties']['title']
    sclient.add_files(files_sheet_id,
                      files_sheets[0]['properties']['sheetId'],
                      mgmt_sheet_id,
                      mgmt_sheets[0]['properties']['sheetId'],
                      files)
    result = client.grant_access_from_anyone(r['id'])
    logger.info('Grant access: {}'.format(result))
    link = client.get_file_link(r['id'])
    logger.info('Link: {}'.format(link))
    return {'status': 'complete', 'url': link}

@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
@must_have_valid_hash()
def iqbrims_create_filelist(**kwargs):
    node = kwargs['node'] or kwargs['project']
    iqbrims = node.get_addon('iqbrims')
    folder = kwargs['folder']
    folder_name = REVIEW_FOLDERS[folder]
    try:
        access_token = iqbrims.fetch_access_token()
    except exceptions.InvalidAuthError:
        raise HTTPError(403)

    client = IQBRIMSClient(access_token)
    folders = client.folders(folder_id=iqbrims.folder_id)
    folders = [f for f in folders if f['title'] == folder_name]
    assert len(folders) > 0
    files = client.files(folder_id=folders[0]['id'])
    index_filename = '.files.txt'
    content_files = [f for f in files if f['title'] != index_filename]
    index_files = [f for f in files if f['title'] == index_filename]
    content_str = u''.join([u'{}\n'.format(f['title']) for f in content_files])
    mime_type = 'text/plain'
    content = content_str.encode('utf8')

    logger.debug(u'Result files: {}'.format([f['title'] for f in files]))

    if len(index_files) == 0:
        client.create_content(folders[0]['id'], index_filename, mime_type, content)
    else:
        client.update_content(index_files[0]['id'], mime_type, content)
    return {'status': 'complete'}

@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
@must_have_valid_hash()
def iqbrims_close_index(**kwargs):
    drop_all = int(request.args.get('all', default='1'))
    node = kwargs['node'] or kwargs['project']
    iqbrims = node.get_addon('iqbrims')
    folder_name = REVIEW_FOLDERS['raw']
    try:
        access_token = iqbrims.fetch_access_token()
    except exceptions.InvalidAuthError:
        raise HTTPError(403)
    client = IQBRIMSClient(access_token)
    folders = client.folders(folder_id=iqbrims.folder_id)
    folders = [f for f in folders if f['title'] == folder_name]
    assert len(folders) > 0
    files = client.files(folder_id=folders[0]['id'])
    files = [f for f in files if f['title'] == settings.INDEXSHEET_FILENAME]
    logger.debug(u'Result files: {}'.format([f['title'] for f in files]))
    if len(files) == 0:
        raise HTTPError(404)
    result = client.revoke_access_from_anyone(files[0]['id'], drop_all=drop_all)
    logger.info('Revoke access: {}'.format(result))
    return {'status': 'complete'}

@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
@must_have_valid_hash()
def iqbrims_get_message(**kwargs):
    node = kwargs['node'] or kwargs['project']
    logger.info('Get Message: {}'.format(request.data))
    data = json.loads(request.data)
    messageid = data['notify_type']
    variables = data['variables']
    management_node = _get_management_node(node)
    management_node_addon = IQBRIMSNodeSettings.objects.get(owner=management_node)
    if management_node_addon is None:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, 'IQB-RIMS addon disabled in management node')
    try:
        access_token = management_node_addon.fetch_access_token()
    except exceptions.InvalidAuthError:
        raise HTTPError(403)
    user_settings = IQBRIMSWorkflowUserSettings(access_token, management_node_addon.folder_id)
    messages = user_settings.MESSAGES
    if messageid not in messages:
        return {'notify_type': messageid}
    msg = messages[messageid].copy()
    for k, v in msg.items():
        if type(v) != str:
            continue
        msg[k] = embed_variables(v, variables)
    msg['notify_type'] = messageid
    return msg

def _iqbrims_get_drive_url(client, root_folder_id, status):
    logger.debug('Retrieving Drive URL...')
    base_folders = None
    r = {}
    for part in REVIEW_FOLDERS.keys():
        has_uploadable = _iqbrims_has_uploadable(status, part)
        if not has_uploadable:
            continue
        if base_folders is None:
            logger.debug('Retrieving files...')
            base_folders = client.folders(folder_id=root_folder_id)
        folder_name = REVIEW_FOLDERS[part]
        folders = [f for f in base_folders if f['title'] == folder_name]
        if len(folders) == 0:
            logger.warn(f'No folders: {root_folder_id}, {folder_name}')
            continue
        folder_id = folders[0]['id']
        r[f'workflow_{part}_link'] = client.get_folder_link(folder_id)
        logger.info(f'Retrieved Google Drive for {part}')
    return r

def _iqbrims_import_auth_from_management_node(node, node_addon, management_node):
    """Grant oauth access on user_settings of management_node and
    set reference of user_settings and external_account of management_node
    instead of copying external settings.
    """
    management_node_addon = IQBRIMSNodeSettings.objects.get(owner=management_node)
    if management_node_addon is None:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, 'IQB-RIMS addon disabled in management node')
    management_user_addon = management_node_addon.user_settings
    if management_user_addon is None:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, 'IQB-RIMS addon is not authorized in management node')
    management_external_account = management_node_addon.external_account
    if management_external_account is None:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, 'IQB-RIMS addon is not authorized in management node')

    management_user_addon.grant_oauth_access(
        node=node,
        external_account=management_external_account
    )

    node_addon.user_settings = management_user_addon
    node_addon.external_account = management_external_account
    node_addon.nodelogger.log(action='node_authorized', save=True)
    node_addon.save()

def _get_management_node(node):
    inst_ids = node.affiliated_institutions.values('id')
    if len(inst_ids) == 0:
        logger.error('node.affiliated_institutions is not set')
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)
    try:
        opt = RdmAddonOption.objects.filter(
            provider=SHORT_NAME,
            institution_id__in=Subquery(inst_ids),
            management_node__isnull=False,
            is_allowed=True
        ).first()
        if opt is None:
            raise HTTPError(http_status.HTTP_403_FORBIDDEN)
    except RdmAddonOption.DoesNotExist:
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)
    return opt.management_node

def _iqbrims_set_status(node, status, auth=None):
    iqbrims = node.get_addon('iqbrims')
    with transaction.atomic():
        all_status = iqbrims.get_status()
        last_status = all_status.copy()
        all_status.update(status)
        logger.info('Status: patch={}, all={}'.format(status, all_status))
        if all_status['state'] in ['deposit', 'check'] and 'labo_id' in all_status:
            register_type = all_status['state']
            labo_name = all_status['labo_id']

            management_node = _get_management_node(node)
            management_node_addon = IQBRIMSNodeSettings.objects.get(owner=management_node)
            if management_node_addon is None:
                raise HTTPError(http_status.HTTP_400_BAD_REQUEST, 'IQB-RIMS addon disabled in management node')
            if last_status['state'] != register_type:
                try:
                    access_token = management_node_addon.fetch_access_token()
                except exceptions.InvalidAuthError:
                    raise HTTPError(403)
                user_settings = IQBRIMSWorkflowUserSettings(access_token, management_node_addon.folder_id)
                app_id = iqbrims.get_process_definition_id(register_type=register_type, user_settings=user_settings)
                flowable = IQBRIMSFlowableClient(app_id, user_settings)
                logger.info('Starting...: app_id={} project_id={}'.format(app_id, node._id))
                flowable.start_workflow(node._id, node.title, all_status,
                                        iqbrims.get_secret())

            # import auth
            _iqbrims_import_auth_from_management_node(node, iqbrims, management_node)

            # create folder
            client, root_folder = _iqbrims_init_folders(node, management_node, register_type, labo_name)

            # mount container
            iqbrims.set_folder(root_folder, auth=auth)
            iqbrims.save()
            if 'is_dirty' not in all_status or not all_status['is_dirty']:
                _iqbrims_update_spreadsheet(node, management_node, register_type, all_status)
            _iqbrims_update_drive_permissions(client, root_folder, last_status, all_status)

        iqbrims.set_status(all_status)
    return all_status

def _iqbrims_init_folders(node, management_node, register_type, labo_name):
    management_node_addon = IQBRIMSNodeSettings.objects.get(owner=management_node)
    if management_node_addon is None:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, 'IQB-RIMS addon disabled in management node')
    folder_id = management_node_addon.folder_id

    try:
        access_token = management_node_addon.fetch_access_token()
    except exceptions.InvalidAuthError:
        raise HTTPError(403)

    client = IQBRIMSClient(access_token)

    _, res = client.create_folder_if_not_exists(folder_id, register_type)
    _, res = client.create_folder_if_not_exists(res['id'], labo_name)
    root_folder_title = get_folder_title(node)
    _, res = client.create_folder_if_not_exists(res['id'], root_folder_title)
    root_folder_id = res['id']
    for key, title in REVIEW_FOLDERS.items():
        if register_type == 'check' and key in ['checklist', 'raw']:
            continue
        client.create_folder_if_not_exists(root_folder_id, title)

    return (client, {
        'id': res['id'],
        'path': '/'.join([
            management_node_addon.folder_path,
            register_type,
            labo_name,
            root_folder_title
        ]) + '/',
    })

def _iqbrims_update_drive_permissions(client, root_folder, last_status, all_status):
    base_folders = client.folders(folder_id=root_folder['id'])
    for part in REVIEW_FOLDERS.keys():
        last_has_uploadable = _iqbrims_has_uploadable(last_status, part)
        all_has_uploadable = _iqbrims_has_uploadable(all_status, part)
        if last_has_uploadable == all_has_uploadable:
            continue
        folder_name = REVIEW_FOLDERS[part]
        folders = [f for f in base_folders if f['title'] == folder_name]
        if len(folders) == 0:
            logger.warn(f'No folders: {folder_name}')
            continue
        folder_id = folders[0]['id']
        if all_has_uploadable:
            logger.info(f'Grant access folder={folder_id}')
            client.grant_access_from_anyone(folder_id)
        else:
            logger.info(f'Revoke access folder={folder_id}')
            client.revoke_access_from_anyone(folder_id)

def _iqbrims_has_uploadable(status, part):
    key = f'workflow_{part}_permissions'
    if key not in status:
        return False
    if not status[key]:
        return False
    return 'UPLOADABLE' in status[key]

def _iqbrims_update_spreadsheet(node, management_node, register_type, status):
    management_node_addon = IQBRIMSNodeSettings.objects.get(owner=management_node)
    if management_node_addon is None:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, 'IQB-RIMS addon disabled in management node')
    folder_id = management_node_addon.folder_id
    try:
        access_token = management_node_addon.fetch_access_token()
    except exceptions.InvalidAuthError:
        raise HTTPError(403)
    client = IQBRIMSClient(access_token)
    user_settings = IQBRIMSWorkflowUserSettings(access_token, folder_id)
    _, rootr = client.create_folder_if_not_exists(folder_id, register_type)
    _, r = client.create_spreadsheet_if_not_exists(rootr['id'],
                                                   settings.APPSHEET_FILENAME)
    sclient = SpreadsheetClient(r['id'], access_token)
    sheets = [s
              for s in sclient.sheets()
              if s['properties']['title'] == settings.APPSHEET_SHEET_NAME]
    logger.info('Spreadsheet: id={}, sheet={}'.format(r['id'], sheets))
    if len(sheets) == 0:
        sclient.add_sheet(settings.APPSHEET_SHEET_NAME)
        sheets = [s
                  for s in sclient.sheets()
                  if s['properties']['title'] == settings.APPSHEET_SHEET_NAME]
    assert len(sheets) == 1
    sheet_id = sheets[0]['properties']['title']
    acolumns = settings.APPSHEET_DEPOSIT_COLUMNS \
               if register_type == 'deposit' \
               else settings.APPSHEET_CHECK_COLUMNS
    columns = sclient.ensure_columns(sheet_id,
                                     [c for c, __ in acolumns])
    column_index = columns.index([c for c, cid in acolumns
                                  if cid == '_node_id'][0])
    row_max = sheets[0]['properties']['gridProperties']['rowCount']
    values = sclient.get_row_values(sheet_id, column_index, row_max)
    logger.info('IDs: {}'.format(values))
    iqbrims = node.get_addon('iqbrims')
    folder_link = client.get_folder_link(iqbrims.folder_id)
    logger.info('Link: {}'.format(folder_link))
    if node._id not in values:
        logger.info('Inserting: {}'.format(node._id))
        v = _iqbrims_fill_spreadsheet_values(node, status, folder_link,
                                             columns, ['' for c in columns],
                                             user_settings)
        sclient.add_row(sheet_id, v)
    else:
        logger.info('Updating: {}'.format(node._id))
        row_index = values.index(node._id)
        v = sclient.get_row(sheet_id, row_index, len(columns))
        v += ['' for __ in range(len(v), len(columns))]
        v = _iqbrims_fill_spreadsheet_values(node, status, folder_link,
                                             columns, v,
                                             user_settings)
        sclient.update_row(sheet_id, v, row_index)

def _iqbrims_filled_index(user_settings, access_token, f):
    sclient = SpreadsheetClient(f['id'], access_token)
    sheets = [s
              for s in sclient.sheets()
              if s['properties']['title'] == user_settings.INDEXSHEET_MANAGEMENT_SHEET_NAME]
    assert len(sheets) == 1
    sheet_props = sheets[0]['properties']
    sheet_id = sheet_props['title']
    col_count = sheet_props['gridProperties']['columnCount']
    logger.info('Grid: cols={}'.format(col_count))
    columns = sclient.get_column_values(sheet_id, 1, col_count)
    fills = sclient.get_row_values(sheet_id, columns.index('Filled'), 2)
    procs = [fill for fill in fills if fill != 'TRUE']
    return len(procs) == 0

def _iqbrims_reset_index(user_settings, access_token, f):
    client = IQBRIMSClient(access_token)
    client.grant_access_from_anyone(f['id'])

    sclient = SpreadsheetClient(f['id'], access_token)
    sheets = [s
              for s in sclient.sheets()
              if s['properties']['title'] == user_settings.INDEXSHEET_MANAGEMENT_SHEET_NAME]
    assert len(sheets) == 1
    sheet_props = sheets[0]['properties']
    sheet_id = sheet_props['title']
    col_count = sheet_props['gridProperties']['columnCount']
    columns = sclient.get_column_values(sheet_id, 1, col_count)
    row = sclient.get_column_values(sheet_id, 2, columns.index('Filled'))
    row[-1] = 'FALSE'
    sclient.update_row(sheet_id, row, 0)

def _iqbrims_fill_spreadsheet_values(node, status, folder_link, columns,
                                     values, user_settings):
    assert len(columns) == len(values), values
    acolumns = settings.APPSHEET_DEPOSIT_COLUMNS \
               if status['state'] == 'deposit' \
               else settings.APPSHEET_CHECK_COLUMNS
    values = list(values)
    for i, col in enumerate(columns):
        tcols = [cid for c, cid in acolumns if c == col]
        if len(tcols) == 0:
            continue
        tcol = tcols[0]
        if tcol is None:
            pass
        elif tcol == '_updated':
            values[i] = datetime.now().strftime('%Y/%m/%d')
        elif tcol == '_node_id':
            values[i] = node._id
        elif tcol == '_node_owner':
            values[i] = node.creator.fullname
        elif tcol == '_node_mail':
            values[i] = node.creator.username
        elif tcol == '_node_title':
            values[i] = node.title
        elif tcol == '_node_contributors':
            values[i] = ','.join([u.fullname for u in node.contributors])
        elif tcol == '_labo_name':
            labos = [l['text']
                     for l in user_settings.LABO_LIST
                     if l['id'] == status['labo_id']]
            values[i] = labos[0] if len(labos) > 0 \
                        else 'Unknown ID: {}'.format(status['labo_id'])
        elif tcol == '_drive_url':
            values[i] = folder_link
        else:
            assert not tcol.startswith('_')
            values[i] = status[tcol] if tcol in status else ''
    return values
