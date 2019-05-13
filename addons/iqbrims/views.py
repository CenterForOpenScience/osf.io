# -*- coding: utf-8 -*-
import httplib as http
import logging

from django.db.models import Subquery
from flask import request

from addons.iqbrims.client import IQBRIMSClient, IQBRIMSFlowableClient
from framework.exceptions import HTTPError

from admin.rdm_addons.decorators import must_be_rdm_addons_allowed
from osf.models import AbstractNode, RdmAddonOption
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

logger = logging.getLogger(__name__)

SHORT_NAME = 'iqbrims'
FULL_NAME = 'IQB-RIMS'

REGISTER_TYPE_LIST = ['check', 'deposit']
INITED_FOLDER_TITLE_LIST = [u'最終原稿・組図', u'生データ', u'チェックリスト', u'スキャン結果']

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
        raise HTTPError(httplib.BAD_REQUEST)
    all_status = iqbrims.get_status()
    last_status = all_status.copy()
    all_status.update(status)
    logger.info('Status: patch={}, all={}'.format(status, all_status))
    if all_status['state'] in ['deposit', 'check'] and 'labo_id' in all_status:
        auth = kwargs['auth']
        register_type = all_status['state']
        labo_name = all_status['labo_id']

        if last_status['state'] != register_type:
            app_id = None
            if register_type == 'deposit':
                app_id = settings.FLOWABLE_RESEARCH_APP_ID
            elif register_type == 'check':
                app_id = settings.FLOWABLE_SCAN_APP_ID
            flowable = IQBRIMSFlowableClient(app_id)
            logger.info('Starting...: app_id={} project_id={}'.format(app_id, node._id))
            flowable.start_workflow(node._id, node.title)

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

        # import auth
        _iqbrims_import_auth_from_management_node(node, iqbrims, opt.management_node)

        # create folder
        root_folder = _iqbrims_init_folders(node, opt.management_node, register_type, labo_name)

        # mount container
        iqbrims.set_folder(root_folder, auth=auth)
        iqbrims.save()

    iqbrims.set_status(all_status)
    return {'data': {'id': node._id, 'type': 'iqbrims-status',
                     'attributes': iqbrims.get_status()}}

@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
def iqbrims_post_notify(**kwargs):
    node = kwargs['node'] or kwargs['project']
    iqbrims = node.get_addon('iqbrims')
    # TODO
    logger.info('Notified: {}'.format(request.data))

@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
def iqbrims_get_storage(**kwargs):
    node = kwargs['node'] or kwargs['project']
    iqbrims = node.get_addon('iqbrims')
    folder = kwargs['folder']
    # TODO
    logger.info('Checking Storage: {}'.format(folder))
    return {'status': 'complete'}

@must_have_addon(SHORT_NAME, 'node')
@must_have_permission(permissions.WRITE)
@must_be_rdm_addons_allowed(SHORT_NAME)
def iqbrims_register_paper(auth, node_addon, pid, **kwargs):
    register_type = request.json.get('register_type', None)
    if not isinstance(register_type, basestring) or register_type not in REGISTER_TYPE_LIST:
        raise HTTPError(http.BAD_REQUEST)
    labo_name = request.json.get('labo_name', None)
    if not isinstance(labo_name, basestring) or len(labo_name) == 0:
        raise HTTPError(http.BAD_REQUEST)

    node = AbstractNode.load(pid)
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

    # import auth
    _iqbrims_import_auth_from_management_node(node, node_addon, opt.management_node)

    # create folder
    root_folder = _iqbrims_init_folders(node, opt.management_node, register_type, labo_name)

    # mount container
    node_addon.set_folder(root_folder, auth=auth)
    node_addon.save()

    return {
        'result': {
            'settings': IQBRIMSSerializer().serialize_settings(node_addon, auth.user),
            'config': {
                'folder': root_folder,
                'urls': IQBRIMSSerializer(node_settings=node_addon).addon_serialized_urls,
            },
        },
        'message': 'Successfully imported access token from profile.',
    }


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
    for title in INITED_FOLDER_TITLE_LIST:
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
