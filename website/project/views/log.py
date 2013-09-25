
from framework import User, get_current_user
from ..model import Node, NodeLog
from ..decorators import must_be_valid_project, must_be_contributor_or_public
from .node import _view_project

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

# todo decorate
def get_log(log_id):

    log = NodeLog.load(log_id)
    user = get_current_user()
    node_to_use = Node.load(log.params.get('node')) or Node.load(log.params.get('project'))

    if not node_to_use.is_public and not node_to_use.is_contributor(user):
        return {
            'status' : 'failure',
        }

    project = Node.load(log.params.get('project'))
    node = Node.load(log.params.get('node'))

    log_json = {
        'user_id' : log.user._primary_key if log.user else '',
        'user_fullname' : log.user.fullname if log.user else '',
        'api_key' : log.api_key.label if log.api_key else '',
        'project_url' : project.url() if project else '',
        'node_url' : node.url() if node else '',
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


@must_be_valid_project
@must_be_contributor_or_public
def get_logs(*args, **kwargs):
    project = kwargs['project']
    logs = list(reversed(project.logs._to_primary_keys()))
    if 'count' in kwargs:
        logs = logs[:kwargs['count']]
    return logs
