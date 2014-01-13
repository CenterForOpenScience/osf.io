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

from api import BucketManager
from boto.s3.connection import S3Connection

import time
from datetime import date
import os

@must_be_contributor
@must_have_addon('s3')
def s3_settings(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    user = kwargs['user']
    s3 = node.get_addon('s3')

    s3_user=user.get_addon('s3')
    if not s3_user:
        user.add_addon('s3','user')
        s3_user=user.get_addon('s3')

    s3_user.access_key = request.json.get('access_key', '')
    s3_user.secret_key =  request.json.get('secret_key','')
    s3_user.save()

    s3.user_settings = s3_user
    s3.s3_bucket = request.json.get('s3_bucket','')
    s3.save()
    

@must_be_contributor
@must_have_addon('s3')
def s3_widget_unused(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    s3 = node.get_addon('s3')
    rv = {}
    rv.update(s3.config.to_json())
    return rv

def _page_content(pid, s3):
    #nTODO use bucket name 
    # create new bucket if not found  inform use/ output error
    #try:
    connect = BucketManager.fromAddon(s3)
    data = connect.getHgrid('/project/' + pid + '/s3/') 
    #except Exception:
    #push_status_message("Something went wrong. Are you sure your setting are correct?")
    #Error handling should occur here or one function up
    # ie if usersettings or settings is none etc etc
    
    rv = {
        'complete': True,
        'bucket': s3.s3_bucket,
        'grid': data,
    }
    return rv

@must_be_contributor_or_public
@must_have_addon('s3')
def s3_page(*args, **kwargs):

    user = kwargs['user']
    node = kwargs['node'] or kwargs['project']

    s3 = node.get_addon('s3')

    data = _view_project(node, user)

    rv = _page_content(str(kwargs['pid']), s3)
    rv.update({
        'addon_page_js': s3.config.include_js['page'],
        'addon_page_css': s3.config.include_css['page'],
    })
    rv.update(s3.config.to_json())
    rv.update(data)

    return rv

@must_be_contributor_or_public
@must_have_addon('s3')
def s3_download(*args, **kwargs):
    node = kwargs['node'] or kwargs['project']
    s3 = node.get_addon('s3')

    keyName = kwargs['key']
    if keyName is None:
        raise HTTPError(http.NOT_FOUND)
    connect = BucketManager(S3Connection(s3.user_settings.access_key,s3.user_settings.secret_key),s3.s3_bucket)
    return redirect(connect.downloadFileURL(keyName.replace('&spc',' ').replace('&sl','/')))

@must_be_contributor_or_public
@must_have_addon('s3')
def s3_upload(*args,**kwargs):
    node = kwargs['node'] or kwargs['project']
    s3 = node.get_addon('s3')

    parentFolder = kwargs.get('path')
    if parentFolder is not None:
        parentFolder = parentFolder.replace('&spc',' ').replace('&sl','/')

    upload = request.files.get('file')
    filename = secure_filename(upload.filename)
    connect = BucketManager.fromAddon(s3)
    connect.flaskUpload(upload,filename,parentFolder)
    return [{
            'uid': str(parentFolder) + filename,
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

@must_be_contributor_or_public
@must_have_addon('s3')
def s3_delete(*args,**kwargs):
    node = kwargs['node'] or kwargs['project']
    s3 = node.get_addon('s3')
    dfile = request.json.get('keyPath')
    connect = BucketManager.fromAddon(s3)
    connect.deleteFile(dfile)
    return {}
    #raise Exception

@must_be_contributor_or_public
@must_have_addon('s3')
def render_file(*args, **kwargs):
    user = kwargs['user']
    node = kwargs['node'] or kwargs['project']
    keyName = kwargs['key']

    s3 = node.get_addon('s3')

    rv = _view_project(node, user)

    rv.update({
        'addon_page_js': 'null',
        'addon_page_css': 'null',
        'filename':keyName.replace('&spc',' ').replace('&sl','/')
    })


    return rv

@must_be_contributor_or_public
@must_have_addon('s3')
def s3_new_folder(*args, ** kwargs):
    node = kwargs['node'] or kwargs['project']
    s3 = node.get_addon('s3')
    folderPath =  request.json.get('path').replace('&spc',' ').replace('&sl','/')

    connect = BucketManager.fromAddon(s3)
    connect.createFolder(folderPath)
    return {}

