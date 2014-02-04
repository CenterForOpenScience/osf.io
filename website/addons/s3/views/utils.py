from framework import request

from website.project.decorators import must_have_addon
from website.project.decorators import must_be_contributor, must_be_contributor_or_public

from website.addons.s3.api import create_bucket

from website import models

import datetime

import time
import os
import base64
import urllib
import hmac
import sha


@must_be_contributor
@must_have_addon('s3', 'node')
def generate_signed_url(*args, ** kwargs):
    # TODO Generate file for hgrid and return with signed url

    # Thanks/psuedo credit to http://codeartists.com/post/36892733572/how-to-directly-upload-files-to-amazon-s3-from-your
    # not really sure how or where to put that....
    node = kwargs['node'] or kwargs['project']
    s3 = node.get_addon('s3')

    file_name = urllib.quote_plus(request.json.get('name'))

    expires = int(time.time() + 10)

    amz_headers = 'x-amz-acl:private'

    mime = request.json.get('type') or 'application/octet-stream'

    request_to_sign = str("PUT\n\n{mime_type}\n{expires}\n{amz_headers}\n/{resource}".format(
        mime_type=mime, expires=expires, amz_headers=amz_headers, resource=s3.bucket + '/' + file_name))

    url = 'https://s3.amazonaws.com/{bucket}/{filename}'.format(
        filename=file_name, bucket=s3.bucket)

    signed = urllib.quote_plus(base64.encodestring(
        hmac.new(str(s3.node_secret_key), request_to_sign, sha).digest()).strip())

    # move into crud.py add a call back in hgrid upload
    node.add_log(
        action='s3_' + models.NodeLog.FILE_ADDED,
        params={
            'project': node.parent_id,
            'node': node._primary_key,
            'bucket': s3.bucket,
            'path': file_name,
        },
        user=kwargs['user'],
        api_key=None,
        log_date=datetime.datetime.utcnow(),
    )

    # TODO Fix me up
    faux_file = [{
        'uid': 'uid',
        'type': 'file',
        'name': file_name,
        'parent_uid': 'fillmein',
        'version_id': 'current',
        'size': '--',
        'lastMod': "--",
        'ext': os.path.splitext(file_name)[1][1:] or '',
        'uploadUrl': " ",
        'downloadUrl': '/project/' + str(kwargs['pid']) + '/s3/download/',
        'deleteUrl': '/project/' + str(kwargs['pid']) + '/s3/delete/',
    }]

    return '{url}?AWSAccessKeyId={access_key}&Expires={expires}&Signature={signed}'.format(url=url, access_key=s3.node_access_key, expires=expires, signed=signed),
    #/blackhttpmagick


@must_be_contributor_or_public
@must_have_addon('s3', 'node')
def create_new_bucket(*args, **kwargs):
    user = kwargs['user']
    user_settings = user.get_addon('s3')
    if create_bucket(user_settings, request.json.get('bucket_name')):
        return {}, 200
    else:
        return {}, 400


def get_cache_file_name(key_name, etag):
    return '{0}_{1}.html'.format(key_name.replace('/', ''), etag)
