from framework import User, request, get_current_user
from framework.auth import get_api_key
from ..model import Node, NodeLog
from ..decorators import must_be_valid_project

from framework import HTTPError
import httplib as http


def get_log(log_id):

    log = NodeLog.load(log_id)
    node_to_use = log.node
    user = get_current_user()
    api_key = get_api_key()

    if not node_to_use.can_edit(user, api_key) and not node_to_use.are_logs_public:
        raise HTTPError(http.FORBIDDEN)
    return {'log': log.serialize()}


#todo: hide private logs of children
@must_be_valid_project
def get_logs(*args, **kwargs):
    user = get_current_user()
    api_key = get_api_key()
    node_to_use = kwargs['node'] or kwargs['project']

    if not node_to_use.can_edit(user, api_key) and not node_to_use.are_logs_public:
        raise HTTPError(http.FORBIDDEN)

    logs = list(reversed(node_to_use.logs._to_primary_keys()))
    if 'count' in request.args:
        count = int(request.args['count'])
    elif 'count' in kwargs:
        count = kwargs['count']
    else:
        count = 10
    logs = logs[:count]
    return {'logs' : logs}
