from framework import request

from website.project.decorators import must_have_addon
from website.project.decorators import must_be_contributor

from website.addons.s3.api import S3Wrapper
from website.addons.s3.api import create_limited_user

from website.addons.s3.utils import getHgrid

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



    #move into crud.py add a call back in hgrid upload
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


def _page_content(pid, s3, user_settings):
    # TODO create new bucket if not found  inform use/ output error?
    if not pid or not s3.bucket or not s3.node_auth or not user_settings or not user_settings.has_auth:
        return {}
    # try:
    # FIX ME SOME HOW
    connect = S3Wrapper.from_addon(s3)
    data = getHgrid('/api/v1/project/' + pid + '/s3/', connect)
    # except S3ResponseError:
    #     push_status_message("It appears you do not have access to this bucket. Are you settings correct?")
    #     data = None
    # Error handling should occur here or one function up
    # ie if usersettings or settings is none etc etc

    rv = {
        'complete': data is not None,
        'bucket': s3.bucket,
        'grid': data,
    }
    return rv


def _s3_create_access_key(s3_user, s3_node):
    u = create_limited_user(
        s3_user.access_key, s3_user.secret_key, s3_node.bucket)

    if u:
        s3_node.node_access_key = u['access_key_id']
        s3_node.node_secret_key = u['secret_access_key']

        s3_node.save()
        return True
    return False
