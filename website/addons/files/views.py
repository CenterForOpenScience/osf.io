"""

"""

import httplib as http

from framework import request
from framework.exceptions import HTTPError
from website.project.decorators import must_be_contributor

@must_be_contributor
def files_disable(**kwargs):

    node = kwargs.get('node') or kwargs.get('project')
    try:
        node.addons_enabled.remove('files')
        node.save()
    except ValueError:
        pass
