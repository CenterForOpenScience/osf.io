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

from api import BucketManager
from boto.s3.connection import S3Connection

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

def _page_content(node, s3):
    #nTODO use bucket name 
    # create new bucket if not found  inform use/ output error
    #try:
    connect = BucketManager(S3Connection(s3.user_settings.access_key,s3.user_settings.secret_key),s3.s3_bucket)
    data = connect.getHgrid()
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

    rv = _page_content(node, s3)
    rv.update({
        'addon_page_js': s3.config.include_js['page'],
        'addon_page_css': s3.config.include_css['page'],
    })
    rv.update(s3.config.to_json())
    rv.update(data)

    return rv