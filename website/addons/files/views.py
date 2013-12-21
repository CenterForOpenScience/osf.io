"""

"""

import httplib as http

from framework import request
from framework.exceptions import HTTPError
from website.project.decorators import must_be_contributor

#@must_be_contributor
#def github_settings(**kwargs):
#
#    node = kwargs.get('node') or kwargs.get('project')
#    addons = node.addongithubsettings__addons
#    if addons:
#        github = addons[0]
#        github.url = request.json.get('github_url', '')
#        github.save()
#    else:
#        raise HTTPError(http.BAD_REQUEST)

@must_be_contributor
def files_disable(**kwargs):

    node = kwargs.get('node') or kwargs.get('project')
    try:
        node.addons_enabled.remove('files')
        node.save()
    except ValueError:
        pass
