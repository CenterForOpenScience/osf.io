import re
import time
import base64
import urllib
import hashlib
import hmac
import sha

from urllib import quote
from bson import ObjectId
from dateutil.parser import parse

from boto.iam import IAMConnection
from boto.s3.cors import CORSConfiguration
from boto.exception import BotoServerError

from website.util import rubeus

from api import get_bucket_list
import settings as s3_settings


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


def wrapped_key_to_json(wrapped_key, node):
    urls = build_urls(node, quote(wrapped_key.s3Key.key.encode('utf-8')))
    rv = {
        rubeus.KIND: _key_type_to_rubeus(wrapped_key.type),
        'name': wrapped_key.name,
        'size': (wrapped_key.size, wrapped_key.size) if wrapped_key.size is not None else '--',
        'ext': wrapped_key.extension if wrapped_key.extension is not None else '--',
        'lastMod': wrapped_key.lastMod.strftime("%Y/%m/%d %I:%M %p") if wrapped_key.lastMod is not None else '--',
        'urls': {
            # TODO: Don't use ternary operators here
            'download': urls['download'] if wrapped_key.type == 'file' else None,
            'delete': urls['delete'] if wrapped_key.type == 'file' else None,
            'view': urls['view'] if wrapped_key.type == 'file' else None,
            'fetch': node.api_url + 's3/hgrid/' + wrapped_key.s3Key.key if wrapped_key.type == 'folder' else None,
            'upload': urls['upload'],
        }
    }
    if wrapped_key.type == 'folder':
        rv.update({
            'nodeUrl': node.url,
            'nodeApiUrl': node.api_url,
        })
    return rv


def get_bucket_drop_down(user_settings):
    try:
        return [
            bucket.name
            for bucket in get_bucket_list(user_settings)
        ]
    except BotoServerError:
        return None


def _key_type_to_rubeus(key_type):
    if key_type == 'folder':
        return rubeus.FOLDER
    else:
        return rubeus.FILE


def create_version_list(wrapper, key_name, node):
    versions = wrapper.get_file_versions(key_name)
    return [
        {
            'id': x.version_id if x.version_id != 'null' else 'Pre-versioning',
            'date': parse(x.last_modified).ctime(),
            'download': build_urls(node, key_name, vid=x.version_id, url='download'),
        }
        for x in versions
    ]


def serialize_bucket(s3wrapper):
    return [
        {
            'name': x.name,
            'path': x.s3Key.key,
            'version_id': s3wrapper.bucket.get_key(x.s3Key.key).version_id,
        }
        for x in s3wrapper.get_wrapped_keys()
    ]


def create_osf_user(access_key, secret_key, name):

    connection = IAMConnection(access_key, secret_key)

    user_name = u'osf-{0}'.format(ObjectId())

    try:
        connection.get_user(user_name)
    except BotoServerError:
        connection.create_user(user_name)

    try:
        connection.get_user_policy(
            user_name,
            s3_settings.OSF_USER_POLICY
        )
    except BotoServerError:
        connection.put_user_policy(
            user_name,
            s3_settings.OSF_USER_POLICY_NAME,
            s3_settings.OSF_USER_POLICY
        )

    response = connection.create_access_key(user_name)
    access_key = response['create_access_key_response']['create_access_key_result']['access_key']
    return user_name, access_key


def remove_osf_user(user_settings):
    connection = IAMConnection(user_settings.access_key, user_settings.secret_key)
    connection.delete_access_key(
        user_settings.access_key,
        user_settings.s3_osf_user
    )
    connection.delete_user_policy(
        user_settings.s3_osf_user,
        s3_settings.OSF_USER_POLICY_NAME
    )
    return connection.delete_user(user_settings.s3_osf_user)


def build_urls(node, file_name, url=None, etag=None, vid=None):
    rv = {
        'upload': u'{node_api}s3/'.format(node_api=node.api_url),
        'download': u'{node_url}s3/{file_name}/download/{vid}'.format(node_url=node.url, file_name=file_name, vid='' if not vid else '?vid={0}'.format(vid)),
        'view': u'{node_url}s3/{file_name}/'.format(node_url=node.url, file_name=file_name),
        'delete': u'{node_api}s3/{file_name}/'.format(node_api=node.api_url, file_name=file_name),
        'render': u'{node_api}s3/{file_name}/render/{etag}'.format(node_api=node.api_url,
            file_name=file_name, etag='' if not etag else '?etag={0}'.format(etag)),
        'fetch': u'{node_api}s3/hgrid/{file_name}'.format(node_api=node.api_url, file_name=file_name),
        'info': node.api_url_for('file_delete_info', path=file_name),
    }
    if not url:
        return rv
    else:
        return rv[url]


def get_cache_file_name(key_name, etag):
    return u'{0}_{1}.html'.format(
        hashlib.md5(key_name).hexdigest(),
        etag,
    )


def validate_bucket_name(name):
    validate_name = re.compile('^(?!.*(\.\.|-\.))[^.][a-z0-9\d.-]{2,61}[^.]$')
    return bool(validate_name.match(name))


def generate_signed_url(mime, file_name, s3):

    expires = int(time.time() + 10)
    amz_headers = 'x-amz-acl:private'

    request_to_sign = str("PUT\n\n{mime_type}\n{expires}\n{amz_headers}\n/{resource}".format(
        mime_type=mime, expires=expires, amz_headers=amz_headers, resource=s3.bucket + '/' + file_name))

    url = 'https://s3.amazonaws.com/{bucket}/{filename}'.format(
        filename=file_name, bucket=s3.bucket)

    signed = urllib.quote_plus(base64.encodestring(
        hmac.new(str(s3.user_settings.secret_key), request_to_sign, sha).digest()).strip())

    return '{url}?AWSAccessKeyId={access_key}&Expires={expires}&Signature={signed}'.format(url=url, access_key=s3.user_settings.access_key, expires=expires, signed=signed),
    #/blackhttpmagick
