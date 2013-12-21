"""

"""

import httplib as http

from framework import request
from framework.exceptions import HTTPError
from website.project.decorators import must_be_contributor

@must_be_contributor
def figshare_settings(**kwargs):

    node = kwargs.get('node') or kwargs.get('project')
    addons = node.addonfigsharesettings__addons
    if addons:
        figshare = addons[0]
        figshare.figshare_id = request.json.get('figshare_id', '')
        figshare.save()
    else:
        raise HTTPError(http.BAD_REQUEST)

@must_be_contributor
def figshare_disable(**kwargs):

    node = kwargs.get('node') or kwargs.get('project')
    try:
        node.addons_enabled.remove('figshare')
        node.save()
    except ValueError:
        pass
