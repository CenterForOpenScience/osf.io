"""

"""

import httplib as http

from framework import request
from framework.exceptions import HTTPError
from website.project import decorators

@decorators.must_be_contributor
def files_disable(**kwargs):

    node = kwargs.get('node') or kwargs.get('project')
    try:
        node.addons_enabled.remove('files')
        node.save()
    except ValueError:
        pass
