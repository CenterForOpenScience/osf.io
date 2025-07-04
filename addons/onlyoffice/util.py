# -*- coding: utf-8 -*-
import logging
import requests
from lxml import etree
from osf.models import OSFUser
from osf.utils.permissions import WRITE
from requests.exceptions import RequestException

from . import settings
from . import proof_key as pfkey

logger = logging.getLogger(__name__)

def get_user_info(cookie):
    user = OSFUser.from_cookie(cookie)
    if user:
        user_info = {
            'user_id': user._id,
            'full_name': user.display_full_name(),
            'display_name': user.get_summary().get('user_display_name')
        }
    else:
        logger.warning('onlyoffice: OSFUser.from_cookie returned None.')
        user_info = {
            'user_id': '',
            'full_name': '',
            'display_name': ''
        }
    # logger.info('onlyoffice: get_user_info : user id = {}, fullname = {}, display_name = {}'
    #             .format(user._id, user_info['full_name'], user_info['display_name']))
    return user_info


def get_file_info(file_node, file_version, cookies):
    wburl = file_node.generate_waterbutler_url(version=file_version, meta='', _internal=True)
    logger.debug('onlyoffice: wburl = {}'.format(wburl))

    try:
        response = requests.get(
            wburl,
            headers={'content-type': 'application/json'},
            cookies=cookies
        )
        response.raise_for_status()
    except RequestException as e:
        logger.warning('onlyoffice: get_file_info = {}'.format(e))
        return None

    file_data = response.json().get('data')
    file_info = {
        'name': file_node.name,
        'size': file_data['attributes'].get('size'),
        'mtime': file_data['attributes'].get('modified_utc'),
        'version': ''
    }
    if file_node.provider == 'osfstorage':
        file_info['version'] = file_data['attributes']['extra'].get('version')
    return file_info


def get_file_version(file_node):
    file_version = ''
    if file_node.provider == 'osfstorage':
        file_versions = file_node.versions.all()
        if file_versions is not None and file_versions.exists():
            file_version = file_versions.latest('id').identifier
    return file_version


def _ext_to_app_name_onlyoffice(ext):
    ext_app = {
        'txt': 'text/plain',
        'docx': 'Word',
        'xlsx': 'Excel',
        'pptx': 'PowerPoint'
    }

    app_name = ext_app[ext.lower()]
    return app_name


def _get_onlyoffice_discovery(server):
    try:
        response = requests.get(server + '/hosting/discovery')
        response.raise_for_status()
    except RequestException:
        logger.warning('onlyoffice: Could not get discovery message from onlyoffice.')
        return None
    return response.text


def get_onlyoffice_url(server, mode, ext):
    discovery = _get_onlyoffice_discovery(server)
    if not discovery:
        return None

    parsed = etree.fromstring(bytes(discovery, encoding='utf-8'))
    if parsed is None:
        logger.warning('onlyoffice: Discovery.xml is not a valid XML.')
        return None

    app_name = _ext_to_app_name_onlyoffice(ext)
    if app_name is None:
        logger.warning('onlyoffice: Not supported file extension for editting.')
        return None

    result = parsed.xpath(f"/wopi-discovery/net-zone/app[@name='{app_name}']/action")

    online_url = ''
    for res in result:
        if res.get('name') == mode and res.get('ext') == ext:
            online_url = res.get('urlsrc')
            break
        if app_name == 'text/plain' and res.get('ext') == '':
            # In discoverry messae of app_name = 'text/plain', ext is ''
            online_url = res.get('urlsrc')
            break

    if online_url == '':
        logger.warning('onlyoffice: Supported url not found.')
        return None

    online_url = online_url[:online_url.index('?') + 1]
    return online_url


def get_proof_key(server):
    discovery = _get_onlyoffice_discovery(server)
    if not discovery:
        return None

    parsed = etree.fromstring(bytes(discovery, encoding='utf-8'))
    if parsed is None:
        logger.warning('onlyoffice: Discovery.xml is not a valid XML.')
        return None

    result = parsed.xpath(f'/wopi-discovery/proof-key')
    for res in result:
        val = res.get(f'value')
        oval = res.get(f'oldvalue')
        modulus = res.get(f'modulus')
        omodulus = res.get(f'oldmodulus')
        exponent = res.get(f'exponent')
        oexponent = res.get(f'oldexponent')

    keydata = pfkey.ProofKeyDiscoveryData(
        value=val,
        modulus=modulus,
        exponent=exponent,
        oldvalue=oval,
        oldmodulus=omodulus,
        oldexponent=oexponent)

    return keydata


def check_proof_key(pkhelper, request, access_token):
    url = request.url
    proof = request.headers.get('X-Wopi-Proof')
    proofOld = request.headers.get('X-Wopi-ProofOld')
    timeStamp = int(request.headers.get('X-Wopi-TimeStamp'))

    #logger.info('file_content_view get header X-Wopi Proof =    {}'.format(proof))
    #logger.info('                             X-Wopi_ProofOld = {}'.format(proofOld))
    #logger.info('                             TimeStamp =       {}'.format(timeStamp))
    #logger.info('                             URL =             {}'.format(url))

    if pkhelper.hasKey() is False:
        proof_key = get_proof_key(settings.WOPI_CLIENT_ONLYOFFICE)
        if proof_key is not None:
            pkhelper.setKey(proof_key)
            # logger.info('onlyoffice: check_proof_key pkhelper key initialized.')
        else:
            return False

    check_data = pfkey.ProofKeyValidationInput(access_token, timeStamp, url, proof, proofOld)

    if pkhelper.validate(check_data) is True and pfkey.verify_timestamp(timeStamp) is True:
        # logger.info('onlyoffice: proof key check passed.')
        return True
    else:
        logger.warning('onlyoffice: proof key check return False.')
        return False


def check_permission(user, file_node, target):
    if not user:
        logger.warning('onlyoffice: check_permission: no OSFUser')
        return False
    logger.info('check_permission user : {}'.format(user._id))

    # SEE ALSO: addons/osfstorage/views.py:osfstorage_create_child()
    # checkout: used for OsfStorage
    if file_node.checkout and file_node.checkout._id != user._id:
        return False

    return target.has_permission(user, WRITE)
