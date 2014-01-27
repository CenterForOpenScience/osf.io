from framework import request

from website.project.decorators import must_have_addon
from website.project.decorators import must_be_contributor

from website.addons.s3.api import S3Wrapper
from website.addons.s3.api import create_limited_user

from website.addons.s3.utils import getHgrid

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
        mime_type=mime, expires=expires, amz_headers=amz_headers, resource=s3.s3_bucket + '/' + file_name))

    url = 'https://s3.amazonaws.com/{bucket}/{filename}'.format(
        filename=file_name, bucket=s3.s3_bucket)

    signed = urllib.quote_plus(base64.encodestring(
        hmac.new(str(s3.s3_node_secret_key), request_to_sign, sha).digest()).strip())

    # TODO Fix me up
    faux_file = [{
        'uid': uid,
        'type': 'file',
        'name': filename,
        'parent_uid': 'fillmein',
        'version_id': 'current',
        'size': '--',
        'lastMod': "--",
        'ext': os.path.splitext(filename)[1][1:] or '',
        'uploadUrl': " ",
        'downloadUrl': '/project/' + str(kwargs['pid']) + '/s3/download/',
        'deleteUrl': '/project/' + str(kwargs['pid']) + '/s3/delete/',
    }]

    return '{url}?AWSAccessKeyId={access_key}&Expires={expires}&Signature={signed}'.format(url=url, access_key=s3.s3_node_access_key, expires=expires, signed=signed),
    #/blackhttpmagick


def _page_content(pid, s3):
    # TODO create new bucket if not found  inform use/ output error?
    if not pid or not s3.s3_bucket or not s3.node_auth:
        return {}
    # try:
    # FIX ME SOME HOW
    connect = S3Wrapper.from_addon(s3)
    data = getHgrid('/project/' + pid + '/s3/', connect)
    # except S3ResponseError:
    #     push_status_message("It appears you do not have access to this bucket. Are you settings correct?")
    #     data = None
    # Error handling should occur here or one function up
    # ie if usersettings or settings is none etc etc

    rv = {
        'complete': data is not None,
        'bucket': s3.s3_bucket,
        'grid': data,
    }
    return rv


def _s3_create_access_key(s3_user, s3_node):
    u = create_limited_user(
        s3_user.access_key, s3_user.secret_key, s3_node.s3_bucket)

    if u:
        s3_node.s3_node_access_key = u['access_key_id']
        s3_node.s3_node_secret_key = u['secret_access_key']

        s3_node.save()
        return True
    return False
