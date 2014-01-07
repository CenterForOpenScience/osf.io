"""

"""

import httplib as http

from framework import request
from framework.exceptions import HTTPError
from website.project import decorators
from website.project.decorators import must_be_contributor
from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon

@decorators.must_be_contributor
def s3_settings(**kwargs):

    node = kwargs.get('node') or kwargs.get('project')
    addons = node.addons3settings__addons
    if addons:
        s3 = addons[0]
        s3.access_key = request.json.get('access_key', '')
        s3.secret_key = request.json.get('secret_key','')
        s3.save()
    else:
        raise HTTPError(http.BAD_REQUEST)
    
@must_be_contributor_or_public
@must_have_addon('github')
def get_bucket_list():
    pass

@must_be_contributor_or_public
@must_have_addon('github')
def get_file_list():
    pass