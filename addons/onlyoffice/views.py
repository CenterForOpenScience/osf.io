# -*- coding: utf-8 -*-
from flask import request, Response
from rest_framework import status as http_status
import logging

import requests
import os
import time
from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in
from osf.models import (BaseFileNode, Guid, OSFUser)

from . import util as onlyoffice_util
from . import proof_key as pfkey
from . import settings
from . import token
from website import settings as websettings

logger = logging.getLogger(__name__)

pkhelper = pfkey.ProofKeyHelper()

TIMEOUT = 10

#  wopi CheckFileInfo endpoint

# Do not add decorator, or else online editor will not open.
def onlyoffice_check_file_info(**kwargs):
    access_token = request.args.get('access_token', '')
    if access_token == '':
        return Response(response='onlyoffice check_file_info access_token is None.', status=500)

    # proof key check
    if onlyoffice_util.check_proof_key(pkhelper, request, access_token) is False:
        return Response(response='onlyoffice check_file_info proof key check failed.', status=500)

    jsonobj = token.decrypt(access_token)
    # logger.info('onlyoffice: check_file_info jsonobj = {}'.format(jsonobj))
    if jsonobj is None:
        return Response(response='onlyoffice check_file_info access_token contents is None.', status=500)

    # token check
    file_id = kwargs['file_id']
    if token.check_token(jsonobj, file_id) is False:
        return Response(response='onlyoffice check_file_info file_id does not exist in access_token.', status=500)

    cookie = token.get_cookie(jsonobj)
    user_info = onlyoffice_util.get_user_info(cookie)
    try:
        file_node = BaseFileNode.objects.get(_id=file_id)
    except Exception:
        logger.warning('onlyoffice: user: {} BaseFileNode None.'.format(user_info['user_id']))
        return Response(response='onlyoffice check_file_info exception in BaseFileNode.objects.get.', status=500)

    logger.debug('onlyoffice: check_file_info file_id = {}, file_node.name = {}'.format(file_id, file_node.name))

    file_version = onlyoffice_util.get_file_version(file_node)
    cookies = {websettings.COOKIE_NAME: cookie}
    file_info = onlyoffice_util.get_file_info(file_node, file_version, cookies)
    if file_info is None:
        return Response(response='onlyoffice check_file_info get_file_info returned None.', status=500)

    logger.info('ONLYOFFICE: file opened : user id = {}, fullname = {}, file_name = {}'
                .format(user_info['user_id'], user_info['full_name'], file_info['name']))

    # "Version" value in response must change when the file changes,
    # and version values must never repeat for a given file.
    # See ONLYOFFICE WOPI API spec. check_file_info() property "version".
    if file_version == '':
        version = file_info['mtime']
    else:
        version = file_version

    res = {
        'BaseFileName': file_info['name'],
        'Version': version,
        #'ReadOnly': True,
        'UserCanReview': True,
        'UserCanWrite': True,
        'SupportsRename': True,
        'SupportsReviewing': True,
        'UserId': user_info['user_id'],
        'UserFriendlyName': user_info['display_name'],
    }
    return res

    '''
    Available response parameters and examples for ONLYOFFICE.
        'BaseFileName': 'Word.docx',
        'Version': 'Khirz6zTPdfd7',
        'BrandcrumbBrandName': "NII",
        'BrandcrumbBrandUrl': "https://www.nii.ac.jp",
        'BrandcrumbDocName': "barnd_doc.docx",
        'BrandcrumbFolderName': "Example Folder Name",
        'BrandcrumbFolderUrl': "https://www.nii.ac.jp/foler/",
        'ClosePostMessage': True,
        'EditModulePostMessages': True,
        'EditNotificationPostMessage': True,
        'FileShareingPostMessage': True,
        'FileVersionPostMessages': True,
        'PostMessageOrigin': "http://192.168.1.141",
        'CloseUrl': '',
        'FileShareingUrl': '',
        'FileVersionUrl': '',
        'HostEditUrl': '',
        'DisablePrint': True,
        'FileExension': '.docx',
        'FileNameMaxLength': 32,
        'LastModifiedTime': isomtime,
        'isAnonymousUser': True,
        'UserFriendlyName': 'Friendly name',
        'UserId': '1',
        'ReadOnly': True,
        'UserCanRename': True,
        'UserCanReview': True,
        'UserCanWrite': True,
        'SuuportsRename': True,
        'SupportsReviewing': True,
        'HidePrintOption': False
    '''


#  file content view endpoint

# Do not add decorator, or else online editor will not open.
def onlyoffice_file_content_view(**kwargs):
    access_token = request.args.get('access_token', '')
    if access_token == '':
        return Response(response='onlyoffice file_content_view access_token is None.', status=500)

    # proof key check
    if onlyoffice_util.check_proof_key(pkhelper, request, access_token) is False:
        return Response(response='onlyoffice file_content_view proof key check failed.', status=500)

    jsonobj = token.decrypt(access_token)
    # logger.info('onlyoffice: file_content_view jsonobj = {}'.format(jsonobj))
    if jsonobj is None:
        return Response(response='onlyoffice file_content_view access_token contents is None.', status=500)

    # token check
    file_id = kwargs['file_id']
    if token.check_token(jsonobj, file_id) is False:
        return Response(response='onlyoffice file_content_view file_id does not exist in access_token.', status=500)

    cookie = token.get_cookie(jsonobj)
    user_info = onlyoffice_util.get_user_info(cookie)
    try:
        file_node = BaseFileNode.objects.get(_id=file_id)
    except Exception:
        logger.warning('onlyoffice: user: {} BaseFileNode None.'.format(user_info['user_id']))
        return Response(response='onlyoffice file_content_view exception in BaseFileNode.objects.get.', status=500)

    logger.debug('onlyoffice: file_content_view file_id = {}, file_node.name = {}'.format(file_id, file_node.name))

    file_version = onlyoffice_util.get_file_version(file_node)
    cookies = {websettings.COOKIE_NAME: cookie}
    file_info = onlyoffice_util.get_file_info(file_node, file_version, cookies)
    if file_info is None:
        return Response(response='onlyoffice file_content_view get_file_info return None.', status=500)

    if request.method == 'GET':
        #  wopi GetFile endpoint
        wburl = file_node.generate_waterbutler_url(version=file_version, action='download', direct=None, _internal=True)
        # logger.info('onlyoffice: wburl, cookies = {}  {}'.format(wburl, cookies))
        try:
            response = requests.get(
                url=wburl,
                cookies=cookies,
                stream=True,
                timeout=TIMEOUT
            )
            response.raise_for_status()

            def generate():
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk

            return Response(generate(), status=response.status_code)
        except Exception as err:
            logger.warning('onlyoffice: Error from Waterbutler: user={}, url={}'.format(user_info['user_id'], wburl))
            logger.warning(err)
            raise

    if request.method == 'POST':
        #  wopi PutFile endpoint
        logger.info('ONLYOFFICE: file saved: user id = {}, fullname = {}, file_name = {}'
                    .format(user_info['user_id'], user_info['full_name'], file_info['name']))

        wburl = file_node.generate_waterbutler_url(direct=None, _internal=True) + '?kind=file'
        logger.debug('onlyoffice: wburl = {}'.format(wburl))

        content_length = request.headers.get('content-length')
        logger.debug('onlyoffice: file_content_view: post content-length = {}'.format(content_length))
        try:
            class StreamData():
                def __iter__(self):
                    return self

                def __next__(self):
                    chunk = request.stream.read(8192)
                    if not chunk:
                        raise StopIteration
                    return chunk

                def __len__(self):
                    return int(content_length)

            response = requests.put(
                url=wburl,
                cookies=cookies,
                data=StreamData(),
                timeout=TIMEOUT
            )
            response.raise_for_status()
            return Response(status=response.status_code)
        except Exception as err:
            logger.warning('onlyoffice: Error from Waterbutler: user={}, url={}'.format(user_info['user_id'], wburl))
            logger.warning(err)
            raise

    return Response(response='Unexpected method: {}'.format(request.method), status=500)


# Do not add decorator, or else online editor will not open.
def onlyoffice_lock_file(**kwargs):
    file_id = kwargs['file_id']
    logger.debug('onlyoffice: lock_file: file_id = {}'.format(file_id))

    if request.method == 'POST':
        operation = request.META.get('X-WOPI-Override', None)
        if operation == 'LOCK':
            lockId = request.META.get('X-WOPI-Lock', None)
            logger.debug(f"onlyoffice: Lock: file id: {file_id}, access token: {request.args.get['access_token']}, lock id: {lockId}")
        elif operation == 'UNLOCK':
            lockId = request.META.get('X-WOPI-Lock', None)
            logger.debug(f"onlyoffice: UnLock: file id: {file_id}, access token: {request.args.get['access_token']}, lock id: {lockId}")
        elif operation == 'REFRESH_LOCK':
            lockId = request.META.get('X-WOPI-Lock', None)
            logger.debug(f"onlyoffice: RefreshLock: file id: {file_id}, access token: {request.args.get['access_token']}, lock id: {lockId}")
        elif operation == 'RENAME':
            toName = request.META.get('X-WOPI-RequestedName', None)
            logger.debug(f"onlyoffice: Rename: file id: {file_id}, access token: {request.args.get['access_token']}, toName: {toName}")

    return Response(status=200)   # Status 200


@must_be_logged_in
def onlyoffice_edit_by_onlyoffice(**kwargs):
    guid = kwargs['guid']
    provider = kwargs['provider']
    path = kwargs['path']
    cookie = request.cookies.get(websettings.COOKIE_NAME)

    # logger.info('onlyoffice: cookie = {}'.format(cookie))
    # logger.info('onlyoffice: edit_by_onlyoffice request.path = {}'.format(request.path))
    # logger.info('onlyoffice: edit_by_onlyoffice guid = {}, provider = {}, path = {}'.format(guid, provider, path))

    guid_target = getattr(Guid.load(guid), 'referent', None)
    if guid_target is None:
        msg = 'onlyoffice: GUID not found: {}'.format(guid)
        logger.warning(msg)
        return Response(response=msg, status=500)
    target = guid_target
    file_node = BaseFileNode.resolve_class(provider, BaseFileNode.FILE).get_or_create(target, path)
    if file_node is None:
        msg = 'onlyoffice: file_node is None. provider = {}, target = {}, path = {}'.format(provider, target, path)
        logger.warning(msg)
        return Response(response=msg, status=500)

    extras = {}
    version = file_node.touch(
        request.headers.get('Authorization'),
        **dict(
            extras,
            cookie=cookie
        )
    )
    if version is None:
        msg = 'onlyoffice: file_node is None. provider = {}, target = {}, path = {}'.format(provider, target, path)
        logger.warning(msg)
        return Response(response=msg, status=500)

    file_name = file_node.name or os.path.basename(path)
    file_id = file_node._id

    # logger.info('onlyoffice: file_id = {}'.format(file_id))
    # logger.info('onlyoffice: BaseFileNode.resolve_class file_name = {}'.format(file_name))
    # logger.debug('onlyoffice: edit_by_onlyoffice filenode.target.id = {}'.format(file_node.target._id))

    user = OSFUser.from_cookie(cookie)

    if not onlyoffice_util.check_permission(user, file_node, target):
        logger.warning('onlyoffice: edit_by_onlyoffice check_permission return False. file_node.target._id = {}'.format(file_node.target._id))
        raise HTTPError(http_status.HTTP_403_FORBIDDEN, data=dict(
            message_short='Forbidden',
            message_long='File can not edit. file is checkouted or in read only project.'))

    ext = os.path.splitext(file_name)[1][1:]
    access_token = token.encrypt(cookie, file_id)
    # access_token ttl (ms)
    token_ttl = (time.time() + settings.WOPI_TOKEN_TTL) * 1000

    wopi_client_host = settings.WOPI_CLIENT_ONLYOFFICE
    logger.debug('onlyoffice: edit_online.index_view wopi_client_host = {}'.format(wopi_client_host))

    wopi_url = ''
    wopi_client_url = onlyoffice_util.get_onlyoffice_url(wopi_client_host, 'edit', ext)
    if wopi_client_url:
        wopi_src_host = settings.WOPI_SRC_HOST
        wopi_src = wopi_src_host + '/wopi/files/' + file_id
        # logger.info('onlyoffice: edit_by_onlyoffice.index_view wopi_src = {}'.format(wopi_src))
        wopi_url = wopi_client_url \
            + 'rs=ja-jp&ui=ja-jp'  \
            + '&WOPISrc=' + wopi_src

    # logger.info('onlyoffice: edit_by_online.index_view wopi_url = {}'.format(wopi_url))

    # Get public key for proof-key check from onlyoffice server, if did not have yet.
    if pkhelper.hasKey() is False:
        proof_key = onlyoffice_util.get_proof_key(wopi_client_host)
        if proof_key is not None:
            pkhelper.setKey(proof_key)
            # logger.info('onlyoffice: edit_by_onlyoffice pkhelper key initialized.')

    logger.debug('onlyoffice: edit_by_online.index_view wopi_url = {}'.format(wopi_url))
    context = {
        'wopi_url': wopi_url,
        'access_token': access_token,
        'access_token_ttl': token_ttl,
    }
    return context
