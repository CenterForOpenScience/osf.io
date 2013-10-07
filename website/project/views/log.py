from framework import User, request, get_current_user
from framework.auth import get_api_key
from ..model import Node, NodeLog
from ..decorators import must_be_valid_project

from framework import HTTPError
import httplib as http

def _render_log_contributor(contributor):
    if isinstance(contributor, dict):
        rv = contributor.copy()
        rv.update({'registered' : False})
        return rv
    user = User.load(contributor)
    return {
        'id' : user._primary_key,
        'fullname' : user.fullname,
        'registered' : True,
    }

def get_log(log_id):

    log = NodeLog.load(log_id)
    node_to_use = log.node
    user = get_current_user()
    api_key = get_api_key()

    if not node_to_use.can_edit(user, api_key) and not node_to_use.are_logs_public:
        raise HTTPError(http.FORBIDDEN)

    project = Node.load(log.params.get('project'))
    node = Node.load(log.params.get('node'))

    log_json = {
        'user_id' : log.user._primary_key if log.user else '',
        'user_fullname' : log.user.fullname if log.user else '',
        'api_key' : log.api_key.label if log.api_key else '',
        'project_url' : project.url if project else '',
        'node_url' : node.url if node else '',
        'project_title' : project.title if project else '',
        'node_title' : node.title if node else '',
        'action' : log.action,
        'params' : log.params,
        'category' : 'project' if log.params['project'] else 'component',
        'date' : log.date.strftime('%m/%d/%y %I:%M %p'),
        'contributors' : [_render_log_contributor(contributor) for contributor in log.params.get('contributors', [])],
        'contributor' : _render_log_contributor(log.params.get('contributor', {})),
    }
    return {'log' : log_json}


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
