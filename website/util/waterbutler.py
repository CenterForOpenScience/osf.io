# -*- coding: utf-8 -*-

import requests
import shutil
import os
from api.base.utils import waterbutler_api_url_for
from website import settings
import logging
logger = logging.getLogger(__name__)

def download_file(osf_cookie, file_node, download_path, **kwargs):
    """Download an waterbutler file by streaming its contents while saving,
    so we do not waste memory.
    """
    download_filename = file_node.name
    if not download_filename:
        download_filename = os.path.basename(file_node.path)
    assert download_filename

    full_path = os.path.join(download_path, download_filename)
    file_info = get_node_info(osf_cookie, file_node.target._id, file_node.provider, file_node.path)
    if file_info is None:
        return None

    try:
        response = requests.get(
            file_node.generate_waterbutler_url(action='download', direct=None, _internal=True, **kwargs),
            cookies={settings.COOKIE_NAME: osf_cookie},
            stream=True
        )
    except Exception as err:
        logger.error(err)
        return None

    with open(full_path, 'wb') as f:
        response.raw.decode_content = True
        shutil.copyfileobj(response.raw, f)

    response.close()
    return full_path

def upload_folder_recursive(osf_cookie, pid, local_path, dest_path):
    """Upload all the content (files and folders) inside a folder.
    """
    count = {
        'fail_file': 0,
        'fail_folder': 0
    }
    content_list = os.listdir(local_path)

    for item_name in content_list:
        full_path = os.path.join(local_path, item_name)

        # Upload folder
        if os.path.isdir(full_path):
            folder_response = create_folder(osf_cookie, pid, item_name, dest_path)
            if folder_response.status_code == requests.codes.created:
                folder_id = folder_response.json()['data']['id']
                rec_response = upload_folder_recursive(osf_cookie, pid, full_path, folder_id)
                count['fail_file'] += rec_response['fail_file']
                count['fail_folder'] += rec_response['fail_folder']
            else:
                count['fail_folder'] += 1

        # Upload file
        else:
            file_response = upload_file(osf_cookie, pid, full_path, item_name, dest_path)
            if file_response.status_code != requests.codes.created:
                count['fail_file'] += 1

    return count

def create_folder(osf_cookie, pid, folder_name, dest_path):
    dest_arr = dest_path.split('/')
    response = requests.put(
        waterbutler_api_url_for(
            pid, dest_arr[0], path='/' + os.path.join(*dest_arr[1:]),
            name=folder_name, kind='folder', meta='', _internal=True
        ),
        cookies={
            settings.COOKIE_NAME: osf_cookie
        }
    )
    return response

def upload_file(osf_cookie, pid, file_path, file_name, dest_path):
    response = None
    dest_arr = dest_path.split('/')
    with open(file_path, 'r') as f:
        response = requests.put(
            waterbutler_api_url_for(
                pid, dest_arr[0], path='/' + os.path.join(*dest_arr[1:]),
                name=file_name, kind='file', _internal=True
            ),
            data=f,
            cookies={
                settings.COOKIE_NAME: osf_cookie
            }
        )
    return response

def get_node_info(osf_cookie, pid, provider, path):
    try:
        response = requests.get(
            waterbutler_api_url_for(
                pid, provider, path=path, _internal=True, meta=''
            ),
            headers={'content-type': 'application/json'},
            cookies={settings.COOKIE_NAME: osf_cookie}
        )
    except Exception as err:
        logger.error(err)
        return None

    content = None
    if response.status_code == 200:
        content = response.json()
    response.close()
    return content
