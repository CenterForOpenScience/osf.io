"""

"""

import httplib as http

from framework import request
from framework.exceptions import HTTPError

from website.project.decorators import must_be_contributor
from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon
from website.project.views.node import _view_project

from api import S3

@must_be_contributor
def s3_settings(**kwargs):

    node = kwargs['node'] or kwargs['project']
    s3 = node.get_addon('s3')
    print "======="
  
    print s3.user_settings
    s3.access_key = request.json.get('access_key', '')
    s3.secret_key = request.json.get('secret_key','')
    s3.s3_bucket = request.json.get('s3_bucket','')
    s3.save()
    

@must_be_contributor
@must_have_addon('s3')
def s3_widget(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    s3 = node.get_addon('s3')
    rv = {}
    rv.update(s3.config.to_json())
    return rv

def _page_content(node, s3):

    connect = s3(s3.access_key,s3.secret_key)
    

@must_be_contributor_or_public
@must_have_addon('s3')
def s3_page(*args, **kwargs):

    user = kwargs['user']
    node = kwargs['node'] or kwargs['project']

    s3 = node.get_addon('s3')

    data = _view_project(node, user)

    rv = _page_content(node, s3)

    rv.update(data)

    return rv