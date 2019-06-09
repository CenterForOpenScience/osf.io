# -*- coding: utf-8 -*-
from functools import reduce
import httplib as http
import json
import logging

from django.db.models import Subquery
from flask import request

from addons.iqbrims.client import IQBRIMSClient, IQBRIMSFlowableClient
from framework.auth import Auth
from website.mails import Mail, send_mail
from framework.exceptions import HTTPError

from admin.rdm_addons.decorators import must_be_rdm_addons_allowed
from osf.models import AbstractNode, RdmAddonOption, BaseFileNode
from osf.utils import permissions
from website.project.decorators import (
    must_have_addon,
    must_be_valid_project,
    must_be_addon_authorizer,
    must_have_permission,
)
from website.ember_osf_web.views import use_ember_app
from addons.iqbrims import settings

from addons.base import generic_views, exceptions
from addons.iqbrims.serializer import IQBRIMSSerializer
from addons.iqbrims.models import NodeSettings as IQBRIMSNodeSettings
from addons.iqbrims.utils import must_have_valid_hash

logger = logging.getLogger(__name__)

SHORT_NAME = 'iqbrims'
FULL_NAME = 'IQB-RIMS'

REGISTER_TYPE_LIST = ['check', 'deposit']
REVIEW_FOLDERS = {'paper': u'最終原稿・組図',
                  'raw': u'生データ',
                  'checklist': u'チェックリスト',
                  'scan': u'スキャン結果'}

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
    iqbrims = node.get_addon('iqbrims')
    try:
        status = request.json['data']['attributes']
    except KeyError:
        raise HTTPError(http.BAD_REQUEST)
    all_status = iqbrims.get_status()
    last_status = all_status.copy()
    all_status.update(status)
    logger.info('Status: patch={}, all={}'.format(status, all_status))
    if all_status['state'] in ['deposit', 'check'] and 'labo_id' in all_status:
        auth = kwargs['auth']
        register_type = all_status['state']
        labo_name = all_status['labo_id']

        if last_status['state'] != register_type:
            app_id = iqbrims.get_process_definition_id(register_type)
            flowable = IQBRIMSFlowableClient(app_id)
            logger.info('Starting...: app_id={} project_id={}'.format(app_id, node._id))
            flowable.start_workflow(node._id, node.title, iqbrims.get_secret())
        management_node = _get_management_node(node)

        # import auth
        _iqbrims_import_auth_from_management_node(node, iqbrims, management_node)

        # create folder
        root_folder = _iqbrims_init_folders(node, management_node, register_type, labo_name)

        # mount container
        iqbrims.set_folder(root_folder, auth=auth)
        iqbrims.save()

    iqbrims.set_status(all_status)
    return {'data': {'id': node._id, 'type': 'iqbrims-status',
                     'attributes': iqbrims.get_status()}}

@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
@must_have_valid_hash()
def iqbrims_post_notify(**kwargs):
    node = kwargs['node'] or kwargs['project']
    logger.info('Notified: {}'.format(request.data))
    data = json.loads(request.data)
    notify_type = data['notify_type']
    to = data['to']
    nodes = []
    if 'user' in to:
        nodes.append((node, 'iqbrims_user'))
    if 'admin' in to:
        nodes.append((_get_management_node(node), 'iqbrims_management'))
    for n, email_template in nodes:
        action = 'iqbrims_{}'.format(notify_type)
        n.add_log(
            action=action,
            params={
                'project': n.parent_id,
                'node': node._id,
            },
            auth=Auth(user=node.creator),
        )
        emails = reduce(lambda x, y: x + y,
                        [[e.address for e in u.emails.all()]
                         for u in n.contributors])
        for email in emails:
            send_mail(email, Mail(email_template, action),
                      title=n.title, guid=n._id, author=node.creator,
                      notify_type=notify_type, mimetype='html')

@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
@must_have_valid_hash()
def iqbrims_post_workflow_state(**kwargs):
    node = kwargs['node'] or kwargs['project']
    iqbrims = node.get_addon('iqbrims')
    part = kwargs['part']
    logger.info('Workflow State: {}, {}'.format(part, request.data))
    status = iqbrims.get_status()
    status['workflow_' + part + '_state'] = json.loads(request.data)['state']
    iqbrims.set_status(status)

@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
@must_have_valid_hash()
def iqbrims_get_storage(**kwargs):
    node = kwargs['node'] or kwargs['project']
    iqbrims = node.get_addon('iqbrims')
    folder = kwargs['folder']
    folder_name = None
    file_name = None
    if folder == 'index':
        folder_name = REVIEW_FOLDERS['raw']
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
        files = [f for f in files if f['title'] == file_name]
    folder_path = iqbrims.folder_path
    management_node = _get_management_node(node)
    base_folder_path = management_node.get_addon('googledrive').folder_path
    assert folder_path.startswith(base_folder_path)
    root_folder_path = folder_path[len(base_folder_path):]
    logger.debug(u'Folder path: {}'.format(root_folder_path))
    node_guids = {}
    management_guids = {}
    if len(files) > 0:
        for f in files:
            g = BaseFileNode.resolve_class(SHORT_NAME, BaseFileNode.ANY).get_file_guids(
                materialized_path=u'/{}/{}'.format(folders[0]['title'],
                                                   f['title']),
                provider=SHORT_NAME,
                target=node
            )
            if len(g) > 0:
                node_guids[f['title']] = g[0]
            g = BaseFileNode.resolve_class('googledrive', BaseFileNode.ANY).get_file_guids(
                materialized_path=u'{}{}/{}'.format(root_folder_path,
                                                    folders[0]['title'],
                                                    f['title']),
                provider='googledrive',
                target=management_node
            )
            if len(g) > 0:
                management_guids[f['title']] = g[0]
    logger.info('Guids: node={}, management={}'.format(node_guids, management_guids))

    return {'status': 'complete' if len(files) > 0 else 'processing',
            'root_folder': root_folder_path,
            'guids': node_guids,
            'management': {'id': management_node._id,
                           'guids': management_guids}}

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
    except RdmAddonOption.DoesNotExist:
        raise HTTPError(http.FORBIDDEN)
    return opt.management_node

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
    root_folder_title = u'{0}-{1}'.format(node.title, node._id)
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
