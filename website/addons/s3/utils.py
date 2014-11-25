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
    file_name = file_name.rstrip('/')

    rv = {
        'upload': node.api_url_for('s3_upload'),
        'view': node.web_url_for('s3_view', path=file_name),
        'delete': node.api_url_for('s3_delete', path=file_name),
        'info': node.api_url_for('file_delete_info', path=file_name),
        'fetch': node.api_url_for('s3_hgrid_data_contents', path=file_name),
        'download': u'{}{}'.format(node.api_url_for('s3_download', path=file_name), '' if not vid else '?vid={0}'.format(vid)),
        'render': u'{}{}'.format(node.api_url_for('ping_render', path=file_name), '' if not etag else '?etag={0}'.format(etag)),
    }

    if url:
        return rv[url]
    return rv


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
