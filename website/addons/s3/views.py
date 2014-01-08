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

@must_be_contributor
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
def s3_page(*args, **kwargs):
    user = kwargs.get('user')
    node = kwargs.get('node') or kwargs.get('project')
    addons = node.addonzoterosettings__addons
    if addons:
        zotero = addons[0]
        rv = {
            'addon_title': 'Amazon S3',
            'addon_page': zotero.render_page(),
        }
        rv.update(_view_project(node, user))
        return rv
    else:
        raise HTTPError(http.BAD_REQUEST)