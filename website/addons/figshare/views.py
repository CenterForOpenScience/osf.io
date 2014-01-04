"""

"""

import httplib as http

from framework import request
from framework.exceptions import HTTPError
from website.project import decorators

@decorators.must_be_contributor
def figshare_settings(**kwargs):

    node = kwargs.get('node') or kwargs.get('project')
    addons = node.addonfigsharesettings__addons
    if addons:
        figshare = addons[0]
        figshare.figshare_id = request.json.get('figshare_id', '')
        figshare.save()
    else:
        raise HTTPError(http.BAD_REQUEST)
