# -*- coding: utf-8 -*-
from datetime import datetime
from functools import reduce
import httplib as http
import json
import logging
import urllib
import re

from django.db import transaction
from django.db.models import Subquery
from flask import request

from addons.iqbrims.client import (
    IQBRIMSClient,
    IQBRIMSFlowableClient,
    SpreadsheetClient,
)
from framework.auth import Auth
from website.mails import Mail, send_mail
from framework.exceptions import HTTPError

from osf.models import RdmAddonOption
from website.project.decorators import (
    must_have_addon,
    must_be_valid_project,
    must_be_addon_authorizer,
    must_have_permission,
)
from website import settings as website_settings
from website.ember_osf_web.views import use_ember_app
from addons.iqbrims import settings

from addons.base import generic_views, exceptions
from addons.iqbrims.serializer import IQBRIMSSerializer
from addons.iqbrims.models import NodeSettings as IQBRIMSNodeSettings
from addons.iqbrims.models import REVIEW_FOLDERS
from addons.iqbrims.utils import (
    get_log_actions,
    must_have_valid_hash,
    get_folder_title,
    add_comment
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
@must_be_addon_authorizer(SHORT_NAME)
def iqbrims_folder_list(node_addon, **kwargs):
    """ Returns all the subsequent folders under the folder id passed.
        Not easily generalizable due to `path` kwarg.
    """
    path = request.args.get('path', '')
    folder_id = request.args.get('folder_id', 'root')

    return node_addon.get_folders(folder_path=path, folder_id=folder_id)

@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
def iqbrims_get_status(**kwargs):
    node = kwargs['node'] or kwargs['project']
    iqbrims = node.get_addon('iqbrims')
    status = iqbrims.get_status()
    status['labo_list'] = ['{}:{}'.format(l['id'], l['text'])
                           for l in settings.LABO_LIST]
    status['review_folders'] = REVIEW_FOLDERS
    is_admin = _get_management_node(node)._id == node._id
    status['is_admin'] = is_admin
    if is_admin:
        status['task_url'] = settings.FLOWABLE_TASK_URL
    return {'data': {'id': node._id, 'type': 'iqbrims-status',
                     'attributes': status}}

@must_be_valid_project
@must_have_permission('admin')
@must_have_addon(SHORT_NAME, 'node')
def iqbrims_set_status(**kwargs):
    node = kwargs['node'] or kwargs['project']
    try:
        status = request.json['data']['attributes']
    except KeyError:
        raise HTTPError(http.BAD_REQUEST)

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
    to = data['to']
    notify_title = data['notify_title'] if 'notify_title' in data else None
    notify_body = data['notify_body'] if 'notify_body' in data else None
    notify_body_md = data['notify_body_md'] \
                     if 'notify_body_md' in data else None
    use_mail = data['use_mail'] if 'use_mail' in data else False
    nodes = []
    if 'user' in to:
        nodes.append((node, 'iqbrims_user'))
    if 'admin' in to:
        nodes.append((_get_management_node(node), 'iqbrims_management'))
    action = 'iqbrims_{}'.format(notify_type)
    if notify_body is None:
        log_actions = get_log_actions()
        if action in log_actions:
            notify_body = log_actions[action]
            href_prefix = website_settings.DOMAIN.rstrip('/') + '/'
            href = href_prefix + node.creator._id + '/'
            uname = 'User <a href="{1}">{0}</a>'.format(node.creator.username,
                                                        href)
            notify_body = notify_body.replace('${user}', uname)
            href = href_prefix + node._id + '/'
            nname = 'Paper <a href="{1}">{0}</a>'.format(node.title, href)
            notify_body = notify_body.replace('${node}', nname)
    if notify_body_md is None:
        a_pat = re.compile(r'<a\s+href=[\'"]?(https?://[^>\'"]+)[\'"]?>' +
                           r'(https?://[^>]+)</a>')
        notify_body_md = a_pat.sub(r'\1', notify_body) \
                         if notify_body is not None else ''
    if notify_title is None:
        notify_title = action
    for n, email_template in nodes:
        comment = add_comment(node=n, user=n.creator,
                              title=notify_title,
                              body=notify_body_md)
        n.add_log(
            action=action,
            params={
                'project': n.parent_id,
                'node': node._id,
                'comment': comment._id,
            },
            auth=Auth(user=node.creator),
        )
        if not use_mail:
            continue
        emails = reduce(lambda x, y: x + y,
                        [[e.address for e in u.emails.all()]
                         for u in n.contributors])
        for email in emails:
            send_mail(email, Mail(email_template, notify_title),
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
    _iqbrims_set_status(node, status)

@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
@must_have_valid_hash()
def iqbrims_get_storage(**kwargs):
    node = kwargs['node'] or kwargs['project']
    iqbrims = node.get_addon('iqbrims')
    folder = kwargs['folder']
    folder_name = None
    file_name = None
    validate = None
    if folder == 'index':
        folder_name = REVIEW_FOLDERS['raw']
        file_name = settings.INDEXSHEET_FILENAME
        validate = _iqbrims_filled_index
    else:
        folder_name = REVIEW_FOLDERS[folder]
    try:
        access_token = iqbrims.fetch_access_token()
    except exceptions.InvalidAuthError:
        raise HTTPError(403)
    client = IQBRIMSClient(access_token)
    folders = client.folders(folder_id=iqbrims.folder_id)
    folders = [f for f in folders if f['title'] == folder_name]
    assert len(folders) > 0
    logger.info(u'Checking Storage: {}, {}, {}'.format(folder, folder_name,
                                                       folders[0]['id']))
    files = client.files(folder_id=folders[0]['id'])
    logger.debug(u'Result files: {}'.format([f['title'] for f in files]))
    if file_name is not None:
        files = [f for f in files
                 if f['title'] == file_name and (validate is None or validate(access_token, f))]
    folder_path = iqbrims.folder_path
    management_node = _get_management_node(node)
    base_folder_path = management_node.get_addon('googledrive').folder_path
    assert folder_path.startswith(base_folder_path)
    root_folder_path = folder_path[len(base_folder_path):]
    logger.debug(u'Folder path: {}'.format(root_folder_path))
    node_urls = []
    management_urls = []
    if len(files) > 0:
        for f in files:
            url = website_settings.DOMAIN.rstrip('/') + '/' + node._id + \
                '/files/iqbrims/' + \
                urllib.quote(folders[0]['title'].encode('utf8')) + '/' + \
                urllib.quote(f['title'].encode('utf8'))
            node_urls.append({'title': f['title'], 'url': url})
            url = website_settings.DOMAIN.rstrip('/') + '/' + management_node._id + \
                  '/files/googledrive' + \
                  urllib.quote(root_folder_path) + \
                  urllib.quote(folders[0]['title'].encode('utf8')) + '/' + \
                  urllib.quote(f['title'].encode('utf8'))
            management_urls.append({'title': f['title'], 'url': url})
    logger.info('Urls: node={}, management={}'.format(node_urls, management_urls))

    return {'status': 'complete' if len(files) > 0 else 'processing',
            'root_folder': root_folder_path,
            'urls': node_urls,
            'management': {'id': management_node._id,
                           'urls': management_urls}}

@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
@must_have_valid_hash()
def iqbrims_reject_storage(**kwargs):
    node = kwargs['node'] or kwargs['project']
    iqbrims = node.get_addon('iqbrims')
    folder = kwargs['folder']
    folder_name = None
    file_name = None
    if folder == 'index':
        folder_name = REVIEW_FOLDERS['raw']
    elif folder == 'scan':
        folder_name = REVIEW_FOLDERS[folder]
        file_name = 'scan.pdf'
    else:
        folder_name = REVIEW_FOLDERS[folder]
    try:
        access_token = iqbrims.fetch_access_token()
    except exceptions.InvalidAuthError:
        raise HTTPError(403)
    client = IQBRIMSClient(access_token)
    folders = client.folders(folder_id=iqbrims.folder_id)
    folders = [f for f in folders if f['title'] == folder_name]
    if file_name is not None and len(folders) > 0:
        files = client.files(folder_id=folders[0]['id'])
        files = [f for f in files if f['title'] == file_name]
    else:
        files = []

    folder_path = iqbrims.folder_path
    management_node = _get_management_node(node)
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
        client.delete_file(files[0]['id'])
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
        return {'status': 'rejected',
                'root_folder': root_folder_path}

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
    client = IQBRIMSClient(access_token)
    folders = client.folders(folder_id=iqbrims.folder_id)
    folders = [f for f in folders if f['title'] == folder_name]
    assert len(folders) > 0
    files = client.files(folder_id=folders[0]['id'])
    files = [f for f in files if f['title'] == 'files.txt']
    logger.debug(u'Result files: {}'.format([f['title'] for f in files]))
    if len(files) == 0:
        return {'status': 'processing'}
    files = client.get_content(files[0]['id']).split('\n')
    _, r = client.create_spreadsheet_if_not_exists(folders[0]['id'],
                                                   settings.INDEXSHEET_FILENAME)
    sclient = SpreadsheetClient(r['id'], access_token)
    sheets = [s
              for s in sclient.sheets()
              if s['properties']['title'] == settings.INDEXSHEET_SHEET_NAME]
    logger.info('Spreadsheet: id={}, sheet={}'.format(r['id'], sheets))
    if len(sheets) == 0:
        sclient.add_sheet(settings.INDEXSHEET_SHEET_NAME)
        sheets = [s
                  for s in sclient.sheets()
                  if s['properties']['title'] == settings.INDEXSHEET_SHEET_NAME]
    assert len(sheets) == 1
    sheet_id = sheets[0]['properties']['title']
    sclient.add_files(sheet_id, sheets[0]['properties']['sheetId'], files)
    result = client.grant_access_from_anyone(r['id'])
    logger.info('Grant access: {}'.format(result))
    link = client.get_file_link(r['id'])
    logger.info('Link: {}'.format(link))
    return {'status': 'complete', 'url': link}

@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
@must_have_valid_hash()
def iqbrims_close_index(**kwargs):
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
    result = client.revoke_access_from_anyone(files[0]['id'])
    logger.info('Revoke access: {}'.format(result))
    return {'status': 'complete'}

def _iqbrims_import_auth_from_management_node(node, node_addon, management_node):
    """Grant oauth access on user_settings of management_node and
    set reference of user_settings and external_account of management_node
    instead of copying external settings.
    """
    management_node_addon = IQBRIMSNodeSettings.objects.get(owner=management_node)
    if management_node_addon is None:
        raise HTTPError(http.BAD_REQUEST, 'IQB-RIMS addon disabled in management node')
    management_user_addon = management_node_addon.user_settings
    if management_user_addon is None:
        raise HTTPError(http.BAD_REQUEST, 'IQB-RIMS addon is not authorized in management node')
    management_external_account = management_node_addon.external_account
    if management_external_account is None:
        raise HTTPError(http.BAD_REQUEST, 'IQB-RIMS addon is not authorized in management node')

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
    try:
        opt = RdmAddonOption.objects.filter(
            provider=SHORT_NAME,
            institution_id__in=Subquery(inst_ids),
            management_node__isnull=False,
            is_allowed=True
        ).first()
        if opt is None:
            raise HTTPError(http.FORBIDDEN)
    except RdmAddonOption.DoesNotExist:
        raise HTTPError(http.FORBIDDEN)
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

            if last_status['state'] != register_type:
                app_id = iqbrims.get_process_definition_id(register_type)
                flowable = IQBRIMSFlowableClient(app_id)
                logger.info('Starting...: app_id={} project_id={}'.format(app_id, node._id))
                flowable.start_workflow(node._id, node.title, all_status,
                                        iqbrims.get_secret())
            management_node = _get_management_node(node)

            # import auth
            _iqbrims_import_auth_from_management_node(node, iqbrims, management_node)

            # create folder
            root_folder = _iqbrims_init_folders(node, management_node, register_type, labo_name)

            # mount container
            iqbrims.set_folder(root_folder, auth=auth)
            iqbrims.save()
            _iqbrims_update_spreadsheet(node, management_node, register_type, all_status)

        iqbrims.set_status(all_status)
    return all_status

def _iqbrims_init_folders(node, management_node, register_type, labo_name):
    management_node_addon = IQBRIMSNodeSettings.objects.get(owner=management_node)
    if management_node_addon is None:
        raise HTTPError(http.BAD_REQUEST, 'IQB-RIMS addon disabled in management node')
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

    return {
        'id': res['id'],
        'path': '/'.join([
            management_node_addon.folder_path,
            register_type,
            labo_name,
            root_folder_title
        ]) + '/',
    }

def _iqbrims_update_spreadsheet(node, management_node, register_type, status):
    management_node_addon = IQBRIMSNodeSettings.objects.get(owner=management_node)
    if management_node_addon is None:
        raise HTTPError(http.BAD_REQUEST, 'IQB-RIMS addon disabled in management node')
    folder_id = management_node_addon.folder_id
    try:
        access_token = management_node_addon.fetch_access_token()
    except exceptions.InvalidAuthError:
        raise HTTPError(403)
    client = IQBRIMSClient(access_token)
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
                                             columns, ['' for c in columns])
        sclient.add_row(sheet_id, v)
    else:
        logger.info('Updating: {}'.format(node._id))
        row_index = values.index(node._id)
        v = sclient.get_row(sheet_id, row_index, len(columns))
        v += ['' for __ in range(len(v), len(columns))]
        v = _iqbrims_fill_spreadsheet_values(node, status, folder_link,
                                             columns, v)
        sclient.update_row(sheet_id, v, row_index)

def _iqbrims_filled_index(access_token, f):
    sclient = SpreadsheetClient(f['id'], access_token)
    sheets = [s
              for s in sclient.sheets()
              if s['properties']['title'] == settings.INDEXSHEET_SHEET_NAME]
    assert len(sheets) == 1
    sheet_props = sheets[0]['properties']
    sheet_id = sheet_props['title']
    col_count = sheet_props['gridProperties']['columnCount']
    row_count = sheet_props['gridProperties']['rowCount']
    logger.info('Grid: {}, {}'.format(col_count, row_count))
    columns = sclient.get_column_values(sheet_id, 1, col_count)
    fills = sclient.get_row_values(sheet_id, columns.index('Filled'), 2)
    procs = [fill for fill in fills if fill != 'TRUE']
    return len(procs) == 0

def _iqbrims_fill_spreadsheet_values(node, status, folder_link, columns,
                                     values):
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
            values[i] = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        elif tcol == '_node_id':
            values[i] = node._id
        elif tcol == '_node_owner':
            values[i] = node.creator.fullname
        elif tcol == '_node_mail':
            values[i] = node.creator.username
        elif tcol == '_node_title':
            values[i] = node.title
        elif tcol == '_labo_name':
            labos = [l['text']
                     for l in settings.LABO_LIST
                     if l['id'] == status['labo_id']]
            values[i] = labos[0] if len(labos) > 0 \
                        else 'Unknown ID: {}'.format(status['labo_id'])
        elif tcol == '_drive_url':
            values[i] = folder_link
        else:
            assert not tcol.startswith('_')
            values[i] = status[tcol] if tcol in status else ''
    return values
