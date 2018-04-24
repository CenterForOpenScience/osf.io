"""
Security views.
"""
from flask import request

from website.util import rubeus
from website.project.decorators import must_be_contributor_or_public
from website.project.views.node import _view_project
from website import settings
#from modularodm import Q

from website import util
from osf.models import OSFUser, Guid, RdmFileTimestamptokenVerifyResult, AbstractNode, BaseFileNode
from datetime import datetime
from api.timestamp.timestamptoken_verify import TimeStampTokenVerifyCheck
from api.timestamp.add_timestamp import AddTimestamp
from api.timestamp import local
import requests
import time
import os
import shutil

import logging
logger = logging.getLogger(__name__)


@must_be_contributor_or_public
def get_init_timestamp_error_data_list(auth, node, **kwargs):
    """
     get timestamp error data list (OSF view)
    """
    ctx = _view_project(node, auth, primary=True)
    ctx.update(rubeus.collect_addon_assets(node))
    data_list = RdmFileTimestamptokenVerifyResult.objects.filter(project_id=kwargs.get('pid')).order_by('provider')
    guid = Guid.objects.get(_id=kwargs.get('pid'))
    provider_error_list = []
    provider = None
    error_list = []
    for data in data_list:
        if data.inspection_result_status == local.TIME_STAMP_TOKEN_CHECK_SUCCESS:
            continue;

        if not provider:
            provider = data.provider
        elif provider != data.provider:
            provider_error_list.append({'provider': provider, 'error_list': error_list})
            provider = data.provider
            error_list = []

        if data.inspection_result_status == local.TIME_STAMP_TOKEN_CHECK_NG:
            verify_result_title = 'NG'
        elif data.inspection_result_status == local.TIME_STAMP_TOKEN_NO_DATA:
            verify_result_title = 'NOT TIMESTAMP_TOKEN'
        elif data.inspection_result_status == local.TIME_STAMP_TOKEN_CHECK_FILE_NOT_FOUND:
            verify_result_title = 'NOT TIMESTAMP_VERIFY'
        elif data.inspection_result_status == local.FILE_NOT_EXISTS:
            verify_result_title = 'FILE_NOT_EXISTS'
        else:
            verify_result_title = 'FILE_NOT_FOUND_AND_NOT_TIMESTAMP_VERIFY'

        if not data.update_user:
            operator_user = OSFUser.objects.get(id=data.create_user).fullname
            operator_date = data.create_date.strftime('%Y/%m/%d %H:%M:%S')
        else:
            operator_user = OSFUser.objects.get(id=data.update_user).fullname
            operator_date = data.update_date.strftime('%Y/%m/%d %H:%M:%S')

        if provider == 'osfstorage':
            base_file_data = BaseFileNode.objects.get(_id=data.file_id)
            error_info = {'file_name': base_file_data.name,
                          'file_path': data.path,
                          'file_kind': 'file',
                          'project_id': data.project_id,
                          'file_id': data.file_id,
                          'version': base_file_data.current_version_number,
                          'operator_user': operator_user,
                          'operator_date': operator_date,
                          'verify_result_title': verify_result_title}
        else:
            file_name = os.path.basename(data.path)
            error_info = {'file_name': file_name,
                          'file_path': data.path,
                          'file_kind': 'file',
                          'project_id': data.project_id,
                          'file_id': data.file_id,
                          'version': '',
                          'operator_user': operator_user,
                          'operator_date': operator_date,
                          'verify_result_title': verify_result_title}
        error_list.append(error_info)

    if error_list:
        provider_error_list.append({'provider': provider, 'error_list': error_list})

    ctx['provider_list'] = provider_error_list
    ctx['project_title'] = node.title
    ctx['guid'] = kwargs.get('pid')
    ctx['web_api_url'] = settings.DOMAIN + node.api_url
    return ctx


@must_be_contributor_or_public
def collect_security_trees(auth, node, **kwargs):
    """
    get provider file list
    """
    serialized = _view_project(node, auth, primary=True)
    serialized.update(rubeus.collect_addon_assets(node))
    user_info = OSFUser.objects.get(id=Guid.objects.get(_id=serialized['user']['id']).object_id)
    api_url = util.api_v2_url(api_url_path(kwargs.get('pid')))
    cookie = user_info.get_or_create_cookie()
    cookies = {settings.COOKIE_NAME:cookie}
    headers = {"content-type": "application/json"}
    provider_json_res = None
    file_res = requests.get(api_url, headers=headers, cookies=cookies)
    provider_json_res = file_res.json()
    file_res.close()
    provider_list = []

    for provider_data in provider_json_res['data']:
        waterbutler_meta_url = util.waterbutler_api_url_for(kwargs.get('pid'),
                                                          provider_data['attributes']['provider'],
                                                          '/',
                                                          **dict(waterbutler_meta_parameter()))
        waterbutler_json_res = None
        waterbutler_res = requests.get(waterbutler_meta_url, headers=headers, cookies=cookies)
        waterbutler_json_res = waterbutler_res.json()
        waterbutler_res.close()

        file_list = []
        child_file_list = []
        for file_data in waterbutler_json_res['data']:
            if file_data['attributes']['kind']=='folder':
                child_file_list.extend(waterbutler_folder_file_info(kwargs.get('pid'),
                                                                    provider_data['attributes']['provider'],
                                                                    file_data['attributes']['path'],
                                                                    node, cookies, headers))
            else:
                file_info = None
                basefile_node = BaseFileNode.resolve_class(provider_data['attributes']['provider'],
                                                           BaseFileNode.FILE).get_or_create(node, 
                                                           file_data['attributes']['path'])
                basefile_node.save()
                if provider_data['attributes']['provider'] == 'osfstorage':
                    file_info = {'file_name': file_data['attributes']['name'],
                                 'file_path': file_data['attributes']['materialized'],
                                 'file_kind':file_data['attributes']['kind'],
                                 'file_id': basefile_node._id,
                                 'version': file_data['attributes']['extra']['version']}
                else:
                     file_info = {'file_name': file_data['attributes']['name'],
                                  'file_path': file_data['attributes']['materialized'],
                                  'file_kind': file_data['attributes']['kind'],
                                  'file_id': basefile_node._id,
                                  'version': ''}

                if file_info:
                   file_list.append(file_info)

        file_list.extend(child_file_list)

        if file_list:
           provider_files = {'provider': provider_data['attributes']['provider'], 'provider_file_list':file_list}
           provider_list.append(provider_files)

    serialized.update({'provider_list': provider_list})
    return serialized

@must_be_contributor_or_public
def get_timestamp_error_data(auth, node, **kwargs):
    # timestamp error data to security or admin view
    if request.method == 'POST':
        request_data = request.json
        data = {}
        for key in request_data.keys():
            data.update({key: request_data[key][0]})
    else:
        data = request.args.to_dict()

    cookies = {settings.COOKIE_NAME:auth.user.get_or_create_cookie()}
    headers = {"content-type": "application/json"}
    url = None
    tmp_dir = None
    result = None
    try:
        file_node = BaseFileNode.objects.get(_id=data['file_id'])
        if data['provider'] == 'osfstorage':
            url = file_node.generate_waterbutler_url(**dict(action='download',
                                                     version=data['version'],
                                                     direct=None, _internal=False))

        else:
            url = file_node.generate_waterbutler_url(**dict(action='download',
                                                     direct=None, _internal=False))

        res = requests.get(url, headers=headers, cookies=cookies)
        tmp_dir='tmp_{}'.format(auth.user._id)
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)
        download_file_path = os.path.join(tmp_dir, data['file_name'])
        with open(download_file_path, "wb") as fout:
            fout.write(res.content)
            res.close()

        verify_check = TimeStampTokenVerifyCheck()
        result = verify_check.timestamp_check(auth.user._id, data['file_id'],
                                              node._id, data['provider'], data['file_path'], data['file_name'], tmp_dir)

        shutil.rmtree(tmp_dir)

    except Exception as err:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        logger.exception(err)

    return result


@must_be_contributor_or_public
def add_timestamp_token(auth, node, **kwargs):
    # timestamptoken add method
    # request Get or Post data set
    if request.method == 'POST':
        request_data = request.json
        data = {}
        for key in request_data.keys():
            data.update({key: request_data[key][0]})

    else:
        data = request.args.to_dict()

    cookies = {settings.COOKIE_NAME:auth.user.get_or_create_cookie()}
    headers = {"content-type": "application/json"}
    url = None
    tmp_dir = None
    try:
        if data['provider'] == 'osfstorage':
#            file_node = BaseFileNode.objects.get(_id=data['file_id'])
            file_node = BaseFileNode.objects.get(_id=data['file_id'])
            url = file_node.generate_waterbutler_url(**dict(action='download',
                                                     version=data['version'],
                                                     direct=None, _internal=False))

        else:
            url = file_node.generate_waterbutler_url(**dict(action='download',
                                                     direct=None, _internal=False))


        # Request To Download File
        res = requests.get(url, headers=headers, cookies=cookies)
        tmp_dir='tmp_{}'.format(auth.user._id)
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)
        download_file_path = os.path.join(tmp_dir, data['file_name'])
        with open(download_file_path, "wb") as fout:
            fout.write(res.content)
            res.close()

        addTimestamp = AddTimestamp()
        result = addTimestamp.add_timestamp(auth.user._id, data['file_id'],
                                            node._id, data['provider'], data['file_path'], 
                                            download_file_path, tmp_dir)


        shutil.rmtree(tmp_dir)

    except Exception as err:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
#        logger.exception(err)

    return result


@must_be_contributor_or_public
def collect_security_trees_to_json(auth, node, **kwargs):
    # admin call project to provider file list
    serialized = _view_project(node, auth, primary=True)
    serialized.update(rubeus.collect_addon_assets(node))
    user_info = OSFUser.objects.get(id=Guid.objects.get(_id=serialized['user']['id']).object_id)
    api_url = util.api_v2_url(api_url_path(kwargs.get('pid')))
    cookie = user_info.get_or_create_cookie()
    cookies = {settings.COOKIE_NAME:cookie}
    headers = {"content-type": "application/json"}
    provider_json_res = None
    file_res = requests.get(api_url, headers=headers, cookies=cookies)
    provider_json_res = file_res.json()
    file_res.close()
    provider_list = []

    for provider_data in provider_json_res['data']:
        waterbutler_meta_url = util.waterbutler_api_url_for(kwargs.get('pid'),
                                                          provider_data['attributes']['provider'],
                                                          '/',
                                                          **dict(waterbutler_meta_parameter()))
        waterbutler_json_res = None
        waterbutler_res = requests.get(waterbutler_meta_url, headers=headers, cookies=cookies)
        waterbutler_json_res = waterbutler_res.json()
        waterbutler_res.close()

        file_list = []
        child_file_list = []
        for file_data in waterbutler_json_res['data']:
            if file_data['attributes']['kind']=='folder':
                 child_file_list.extend(waterbutler_folder_file_info(kwargs.get('pid'),
                                                                     provider_data['attributes']['provider'],
                                                                     file_data['attributes']['path'],
                                                                     node, cookies, headers))
            else:
                file_info = None
                basefile_node = BaseFileNode.resolve_class(provider_data['attributes']['provider'],
                                                           BaseFileNode.FILE).get_or_create(node, 
                                                           file_data['attributes']['path'])
                basefile_node.save()
                if provider_data['attributes']['provider'] == 'osfstorage':
                    file_info = {'file_name': file_data['attributes']['name'],
                                 'file_path': file_data['attributes']['materialized'],
                                 'file_kind':file_data['attributes']['kind'],
                                 'file_id': basefile_node._id,
                                 'version': file_data['attributes']['extra']['version']}                                 
                else:
                    file_info = {'file_name': file_data['attributes']['name'],
                                 'file_path': file_data['attributes']['materialized'],
                                 'file_kind': file_data['attributes']['kind'],
                                 'file_id': basefile_node._id,
                                 'version': ''}
                if file_info:
                   file_list.append(file_info)

        file_list.extend(child_file_list)

        if file_list:
           provider_files = {'provider': provider_data['attributes']['provider'], 'provider_file_list':file_list}
           provider_list.append(provider_files)

    return {'provider_list': provider_list}

def waterbutler_folder_file_info(pid, provider, path, node, cookies, headers):
    # get waterbutler folder file 
    if provider == 'osfstorage':
        waterbutler_meta_url = util.waterbutler_api_url_for(pid, provider,
                                                            '/' + path,
                                                            **dict(waterbutler_meta_parameter()))
    else:
        waterbutler_meta_url = util.waterbutler_api_url_for(pid, provider,
                                                            path,
                                                            **dict(waterbutler_meta_parameter()))

    waterbutler_res = requests.get(waterbutler_meta_url, headers=headers, cookies=cookies)
    waterbutler_json_res = waterbutler_res.json()
    waterbutler_res.close()
    file_list = []
    child_file_list = []
    for file_data in waterbutler_json_res['data']:
        if file_data['attributes']['kind']=='folder':
             folder_info = {'file_name': file_data['attributes']['name'],
                            'file_path': file_data['attributes']['materialized'],
                            'file_kind': file_data['attributes']['kind'],
                            'file_id': file_data['attributes']['path']}
             child_file_list.extend(waterbutler_folder_file_info(\
                                                  pid, provider, file_data['attributes']['path'],
                                                  node, cookies, headers))
        else:
             if provider == 'osfstorage':
                  basefile_node = BaseFileNode.resolve_class(provider,
                                                             BaseFileNode.FILE).get_or_create(node,
                                                             file_data['attributes']['path'])
                  basefile_node.save()
                  file_info = {'file_name': file_data['attributes']['name'],
                               'file_path': file_data['attributes']['materialized'],
                               'file_kind': file_data['attributes']['kind'],
                               'file_id': basefile_node._id,
                               'version': file_data['attributes']['extra']['version']}
             else:
                  file_info = {'file_name': file_data['attributes']['name'],
                               'file_path': file_data['attributes']['materialized'],
                               'file_kind': file_data['attributes']['kind'],
                               'file_id': basefile_node._id,
                               'version': ''}

             file_list.append(file_info)

    file_list.extend(child_file_list)

    return file_list

def api_url_path(node_id):
    # creaet node files api url
    return 'nodes/{}/files'.format(node_id)

def waterbutler_meta_parameter():
    # get waterbutler api parameter value
    return {'meta=&_':int(time.mktime(datetime.now().timetuple()))}
