import re
from urllib import quote
from bson import ObjectId
from datetime import datetime

from boto.iam import IAMConnection
from boto.s3.cors import CORSConfiguration
from boto.exception import BotoServerError

from website.util import rubeus

from api import S3Key, get_bucket_list
import settings as s3_settings


#TODO remove if not needed in newest hgrid
def checkFolders(s3wrapper, keyList):
    for k in keyList:
        if k.parentFolder is not None and k.parentFolder not in [x.name for x in keyList]:
            newKey = s3wrapper.create_folder(k.pathTo)
            keyList.append(S3Key(newKey))


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
        s3_settings.ALLOWED_ORIGIN,
        allowed_header=['*'],
        id='osf-s3-{0}'.format(ObjectId()),
    )

    # Save changes
    s3wrapper.set_cors_rules(rules)


def wrapped_key_to_json(wrapped_key, node_api, node_url):
    return {
        rubeus.KIND: _key_type_to_rubeus(wrapped_key.type),
        'name': wrapped_key.name,
        'size': (wrapped_key.size, wrapped_key.size) if wrapped_key.size is not None else '--',
        'ext': wrapped_key.extension if wrapped_key.extension is not None else '--',
        'lastMod': wrapped_key.lastMod.strftime("%Y/%m/%d %I:%M %p") if wrapped_key.lastMod is not None else '--',
        'urls': {
            # TODO: Don't use ternary operators here
            'download': node_url + 's3/' + quote(wrapped_key.fullPath) + '/download/' if wrapped_key.type == 'file' else None,
            'delete': node_api + 's3/' + quote(wrapped_key.fullPath) + '/' if wrapped_key.type == 'file' else None,
            'view': node_url + 's3/' + quote(wrapped_key.fullPath) + '/' if wrapped_key.type == 'file' else None,
            'fetch': node_api + 's3/hgrid/' + wrapped_key.fullPath if wrapped_key.type == 'folder' else None,
            'upload': node_api + 's3/',
        }
    }


def get_bucket_drop_down(user_settings):
    try:
        dropdown_list = ''
        for bucket in get_bucket_list(user_settings):
                dropdown_list += '<li role="presentation"><a href="#">' + \
                    bucket.name + '</a></li>'
        return dropdown_list
    except BotoServerError:
        return False



def _key_type_to_rubeus(key_type):
    if key_type == 'folder':
        return rubeus.FOLDER
    else:
        return rubeus.FILE


def key_upload_path(wrapped_key, url):
    if wrapped_key.type != 'folder':
        return quote(url)
    else:
        return quote(url + '/' + wrapped_key.fullPath + '/')

def create_version_list(wrapper, key_name, node_api):
    versions = wrapper.get_file_versions(key_name)
    return [
        {
            'id': x.version_id if x.version_id != 'null' else 'Pre-versioning',
            'date': _format_date(x.last_modified),
            'download': _get_download_url(key_name, x.version_id, node_api),
        }
        for x in versions
    ]


def _format_date(date):
    m = re.search(
        '(.+?)-(.+?)-(\d*)T(\d*):(\d*):(\d*)', str(date))
    if m is not None:
        dt = datetime(int(m.group(1)), int(m.group(2)),
                      int(m.group(3)), int(m.group(4)), int(m.group(5)))
        return dt.strftime("%Y/%m/%d %I:%M %p")
    else:
        return '--'


def _get_download_url(key_name, version_id, node_api):
    url = node_api + 's3/' + quote(key_name) + '/download/'
    if version_id != 'null':
        return url + '?vid=' + version_id + '/'
    else:
        return url


def serialize_bucket(s3wrapper):
    return [
        {
            'name': x.name,
            'path': x.fullPath,
            'version_id': s3wrapper.bucket.get_key(x.fullPath).version_id,
        }
        for x in s3wrapper.get_wrapped_keys()
    ]

def create_osf_user(access_key, secret_key, name):
    connection = IAMConnection(access_key, secret_key)
    try:
        connection.get_user(s3_settings.OSF_USER.format(name))
    except BotoServerError:
        connection.create_user(s3_settings.OSF_USER.format(name))

    try:
        connection.get_user_policy(
            s3_settings.OSF_USER.format(name),
            s3_settings.OSF_USER_POLICY
        )
    except BotoServerError:
        connection.put_user_policy(
            s3_settings.OSF_USER.format(name),
            s3_settings.OSF_USER_POLICY_NAME,
            s3_settings.OSF_USER_POLICY
        )

    access_key = connection.create_access_key(s3_settings.OSF_USER.format(name))
    return access_key['create_access_key_response']['create_access_key_result']['access_key']


def remove_osf_user(user_settings):
    name = user_settings.owner.family_name
    connection = IAMConnection(user_settings.access_key, user_settings.secret_key)
    connection.delete_access_key(
        user_settings.access_key,
        s3_settings.OSF_USER.format(name)
    )
    connection.delete_user_policy(
        s3_settings.OSF_USER.format(name),
        s3_settings.OSF_USER_POLICY_NAME
    )
    return connection.delete_user(s3_settings.OSF_USER.format(name))
