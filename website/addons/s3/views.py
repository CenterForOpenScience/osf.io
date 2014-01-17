"""

"""

import httplib as http

from framework import request
from framework.exceptions import HTTPError

from website.project.decorators import must_be_contributor
from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon
from website.project.views.node import _view_project
from framework.status import push_status_message
from framework import request, redirect, make_response
from framework.flask import secure_filename
from framework.auth import get_current_user, must_be_logged_in

from api import S3Wrapper
from api import create_limited_user, remove_user, has_access, does_bucket_exist
from boto.exception import S3ResponseError

import time
from datetime import date
import os
import utils
import time, os, json, base64, urllib, hmac, sha

@must_be_logged_in
def s3_user_settings(*args, **kwargs):
    user = kwargs['user']
    s3_user = user.get_addon('s3')

    if not s3_user:
        raise HTTPError(http.BAD_REQUEST)

    s3_access_key = request.json.get('access_key','')
    s3_secret_key = request.json.get('secret_key','')

    has_auth = (s3_access_key and s3_secret_key)

    changed = (
        s3_access_key != s3_user.access_key or
        s3_secret_key != s3_user.secret_key
        )


    if changed:
        if not has_access(s3_access_key,s3_secret_key):
            error_message = ('Looks like your creditials are incorrect'
                             'Could you have mistyped them?')
            return {'message':error_message},400

        s3_user.access_key = s3_access_key
        s3_user.secret_key = s3_secret_key
        s3_user.user_has_auth = has_auth

        s3_user.save()


@must_be_contributor
@must_have_addon('s3', 'node')
def s3_settings(*args, **kwargs):

    user = kwargs['user']

    s3_node = kwargs['node_addon']
    s3_user = user.get_addon('s3')

    # If authorized, only owner can change settings
    if s3_user and s3_user.owner != user:
        raise HTTPError(http.BAD_REQUEST)

    s3_bucket = request.json.get('s3_bucket', '')

    if not s3_bucket or not does_bucket_exist(s3_user.access_key,s3_user.secret_key,s3_bucket):
        error_message = ('Looks like this bucket does not exist.'
                         'Could you have mistyped it?')
        return {'message':error_message},400

    changed = (
        s3_bucket != s3_node.s3_bucket
    )
    # Delete callback
    if changed:

        # Update node settings
        s3_node.s3_bucket = s3_bucket

        s3_node.save()

@must_be_contributor
@must_have_addon('s3', 'node')
def s3_create_access_key(*args, **kwargs):

    user = kwargs['user']

    s3_node = kwargs['node_addon']
    s3_user = user.get_addon('s3')

    u = create_limited_user(s3_user.access_key,s3_user.secret_key,s3_node.s3_bucket)

    if u:

        s3_node.s3_node_access_key = u['access_key_id']
        s3_node.s3_node_secret_key = u['secret_access_key']
        s3_node.node_auth = 1

        s3_node.save()

@must_be_contributor
@must_have_addon('s3','node')
def s3_delete_access_key(*args, **kwargs):
    user = kwargs['user']

    s3_node = kwargs['node_addon']
    s3_user = user.get_addon('s3')

    #delete user from amazons data base
    #boto giveth and boto taketh away
    remove_user(s3_user.access_key,s3_user.secret_key,s3_node.s3_bucket,s3_node.s3_node_access_key)


    #delete our access and secret key
    s3_node.s3_node_access_key = ''
    s3_node.s3_node_secret_key = ''
    s3_node.node_auth = 0
    s3_node.save()


def _page_content(pid, s3):
    #nTODO use bucket name 
    # create new bucket if not found  inform use/ output error
   # try:
    connect = S3Wrapper.from_addon(s3)
    data = utils.getHgrid('/project/' + pid + '/s3/',connect) 
    #except S3ResponseError:
       # push_status_message("It appears you do not have access to this bucket. Are you settings correct?")
       # data = None
    #Error handling should occur here or one function up
    # ie if usersettings or settings is none etc etc

    rv = {
        'complete': s3.node_auth and data is not None,
        'bucket': s3.s3_bucket,
        'grid': data,
    }
    return rv

@must_be_contributor_or_public
@must_have_addon('s3','node')
def s3_page(*args, **kwargs):


    user = kwargs['user']
    node = kwargs['node'] or kwargs['project']

    s3 = node.get_addon('s3')

    data = _view_project(node, user, primary=True)

    rv = _page_content(str(kwargs['pid']), s3)
    rv.update({
        'addon_page_js': s3.config.include_js['page'],
        'addon_page_css': s3.config.include_css['page'],
    })
    rv.update(s3.config.to_json())
    rv.update(data)

    return rv

@must_be_contributor_or_public
@must_have_addon('s3','node')
def s3_download(*args, **kwargs):
    node = kwargs['node'] or kwargs['project']
    s3 = node.get_addon('s3')

    keyName = kwargs['key']
    if keyName is None:
        raise HTTPError(http.NOT_FOUND)
    connect = S3Wrapper.from_addon(s3)
    return redirect(connect.download_file_URL(keyName.replace('&spc',' ').replace('&sl','/')))

@must_be_contributor
@must_have_addon('s3','node')
def s3_upload(*args,**kwargs):
    node = kwargs['node'] or kwargs['project']
    s3 = node.get_addon('s3')

    parentFolder = kwargs.get('path')
    if parentFolder is not None:
        parentFolder = parentFolder.replace('&spc',' ').replace('&sl','/')
    else:
        parentFolder=0

    upload = request.files.get('file')
    filename = secure_filename(upload.filename)
    connect = S3Wrapper.from_addon(s3)
    connect.flask_upload(upload,filename,parentFolder)
    if parentFolder != 0:
        uid = str(parentFolder) + filename
    else:
        uid = filename
    return [{
            'uid': uid,
            'type': 'file',
            'name': filename,
            'parent_uid': parentFolder,
            'version_id': 'current',
            'size': '--',
            'lastMod': "--",
            'ext':os.path.splitext(filename)[1][1:],
            'uploadUrl': " ",
            'downloadUrl':'/project/' + str(kwargs['pid'] )+ '/s3/download/',
            'deleteUrl': '/project/' + str(kwargs['pid'] )+ '/s3/delete/',
        }]

@must_be_contributor
@must_have_addon('s3','node')
def s3_delete(*args,**kwargs):
    node = kwargs['node'] or kwargs['project']
    s3 = node.get_addon('s3')
    dfile = request.json.get('keyPath')
    connect = S3Wrapper.from_addon(s3)
    connect.delete_file(dfile)
    return {}

@must_be_contributor
@must_have_addon('s3','node')
def render_file(*args, **kwargs):
    user = kwargs['user']
    node = kwargs['node'] or kwargs['project']
    keyName = kwargs['key']

    s3 = node.get_addon('s3')

    rv = _view_project(node, user)

    rv.update({
        'addon_page_js': 'null',
        'addon_page_css': 'null',
        'complete': 1,
        'filename':keyName.replace('&spc',' ').replace('&sl','/')
    })

    rv.update(s3.config.to_json())
    return rv

@must_be_contributor
@must_have_addon('s3','node')
def s3_new_folder(*args, ** kwargs):
    node = kwargs['node'] or kwargs['project']
    s3 = node.get_addon('s3')
    folderPath =  request.json.get('path').replace('&spc',' ').replace('&sl','/')

    connect = S3Wrapper.from_addon(s3)
    connect.createFolder(folderPath)
    return {}

@must_be_contributor
@must_have_addon('s3','node')
def generate_signed_url(*args, ** kwargs):
    #Thanks/psuedo credit to http://codeartists.com/post/36892733572/how-to-directly-upload-files-to-amazon-s3-from-your
    #not really sure how or where to put that....
    node = kwargs['node'] or kwargs['project']
    s3 = node.get_addon('s3')

    file_name = urllib.quote_plus(request.json.get('name'))

    expires = int(time.time()+ 10) #Ten seconds for the request to go through might need to be larger....

    amz_headers = "x-amz-acl:public-read"

    mime = request.json.get('type') if request.json.get('type') != "" else 'application/octet-stream'

    request_to_sign = str("PUT\n\n{mime_type}\n{expires}\n{amz_headers}\n/{resource}".format(mime_type=mime,expires=expires,amz_headers=amz_headers,resource=s3.s3_bucket+'/'+file_name))

    print request_to_sign

    url = 'https://s3.amazonaws.com/' + s3.s3_bucket + '/' + file_name
    
    signed = urllib.quote_plus(base64.encodestring(hmac.new(str(s3.s3_node_secret_key), request_to_sign, sha).digest()).strip())

    return {
    'signed_request': '{url}?AWSAccessKeyId={access_key}&Expires={expires}&Signature={signed}'.format(url=url,access_key=s3.s3_node_access_key,expires=expires,signed=signed),
    'url': "http://s3.amazonaws.com/#{bucket}/#{filename}".format(bucket=s3.s3_bucket,filename=file_name)
    }
    #/blackhttpmagick