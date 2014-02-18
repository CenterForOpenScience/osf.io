from bson import ObjectId
from urllib import quote
from dateutil.parser import parse

from boto.iam import IAMConnection
from boto.s3.cors import CORSConfiguration
from boto.exception import BotoServerError

from website.util import rubeus

from api import get_bucket_list
from settings import ALLOWED_ORIGIN, OSF_USER, OSF_USER_POLICY, OSF_USER_POLICY_NAME

URLADDONS = {
    'delete': 's3/delete/',
    'upload': 's3/upload/',
    'download': 's3/download/',
    'view': 's3/view/'
}


def adjust_cors(s3wrapper, clobber=False):
    """Set CORS headers on a bucket, removing pre-existing headers set by the
    OSF. Optionally clear all pre-existing headers.

    :param S3Wrapper s3wrapper: S3 wrapper instance
    :param bool clobber: Remove all pre-existing rules. Note: if this option
        is set to True, remember to warn or prompt the user first!

    """
    rules = s3wrapper.get_cors_rules()

    # Remove some / all pre-existing rules
    if clobber:
        rules = CORSConfiguration([])
    else:
        rules = CORSConfiguration([
            rule
            for rule in rules
            if 'osf-s3' not in (rule.id or '')
        ])

    # Add new rule
    rules.add_rule(
        ['PUT', 'GET'],
        ALLOWED_ORIGIN,
        allowed_header={'*'},
        id='osf-s3-{0}'.format(ObjectId())
    )

    # Save changes
    s3wrapper.set_cors_rules(rules)


def wrapped_key_to_json(wrapped_key, node_api, node_url):
    return {
        rubeus.KIND: _key_type_to_rubeus(wrapped_key.type),
        'name': wrapped_key.name,
        'size': (wrapped_key.size, wrapped_key.size) if wrapped_key.size is not None else '--',
        'lastMod': wrapped_key.lastMod.ctime() if wrapped_key.lastMod is not None else '--',
        'ext': wrapped_key.extension if wrapped_key.extension is not None else '--',
        'urls': {
            'download': node_api + URLADDONS['download'] + quote(wrapped_key.fullPath) + '/' if wrapped_key.type == 'file' else None,
            'delete': node_api + URLADDONS['delete'] + quote(wrapped_key.fullPath) + '/'if wrapped_key.type == 'file' else None,
            'view': node_url + URLADDONS['view'] + quote(wrapped_key.fullPath) + '/'if wrapped_key.type == 'file' else None,
            'fetch': node_api + 's3/hgrid/' + wrapped_key.fullPath if wrapped_key.type == 'folder' else None,
            'upload': node_api + 's3/upload/'
        }
    }


def _key_type_to_rubeus(key_type):
    if key_type == 'folder':
        return rubeus.FOLDER
    else:
        return rubeus.FILE


def key_upload_path(wrapped_key, url):
    if wrapped_key.type != 'folder':
        return quote(url + URLADDONS['upload'])
    else:
        return quote(url + URLADDONS['upload'] + wrapped_key.fullPath + '/')


def get_bucket_drop_down(user_settings):
    try:
        dropdown_list = ''
        for bucket in get_bucket_list(user_settings):
                dropdown_list += '<li role="presentation"><a href="#">' + \
                    bucket.name + '</a></li>'
        return dropdown_list
    except BotoServerError:
        return False


def create_version_list(wrapper, key_name, node_api):
    versions = wrapper.get_file_versions(key_name)
    return [{
            'id': x.version_id if x.version_id != 'null' else 'Pre-versioning',
            'date': parse(x.last_modified).ctime(),
            'download': _get_download_url(key_name, x.version_id, node_api),
            } for x in versions]


def _get_download_url(key_name, version_id, node_api):
    url = node_api + 's3/download/' + quote(key_name) + '/'
    if version_id != 'null':
        return url + '?vid=' + version_id + '/'
    else:
        return url


def serialize_bucket(s3wrapper):
    return [{
            'name': x.name,
            'path': x.fullPath,
            'version_id': s3wrapper.bucket.get_key(x.fullPath).version_id,
            } for x in s3wrapper.get_wrapped_keys()]


def create_osf_user(access_key, secret_key, name):
    connection = IAMConnection(access_key, secret_key)
    try:
        connection.get_user(OSF_USER.format(name))
    except BotoServerError:
        connection.create_user(OSF_USER.format(name))

    try:
        connection.get_user_policy(OSF_USER.format(name), OSF_USER_POLICY)
    except BotoServerError:
        connection.put_user_policy(OSF_USER.format(name), OSF_USER_POLICY_NAME, OSF_USER_POLICY)

    return connection.create_access_key(OSF_USER.format(name))['create_access_key_response']['create_access_key_result']['access_key']


def remove_osf_user(user_settings):
    name = user_settings.owner.family_name
    connection = IAMConnection(user_settings.access_key, user_settings.secret_key)
    connection.delete_access_key(user_settings.access_key, OSF_USER.format(name))
    connection.delete_user_policy(OSF_USER.format(name), OSF_USER_POLICY_NAME)
    return connection.delete_user(OSF_USER.format(name))
