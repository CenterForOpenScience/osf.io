# -*- coding: utf-8 -*-
import httplib as http
import logging

from framework import request
from framework.auth import get_current_user, get_api_key, get_current_node
from framework.auth.decorators import collect_auth, Auth
from framework.exceptions import HTTPError

from website.project.model import NodeLog
from website.project.decorators import must_be_valid_project


logger = logging.getLogger(__name__)

def get_log(log_id):

    log = NodeLog.load(log_id)
    node_to_use = log.node
    auth = Auth(
        user=get_current_user(),
        api_key=get_api_key(),
        api_node=get_current_node(),
    )

    if not node_to_use.can_view(auth):
        raise HTTPError(http.FORBIDDEN)
    return {'log': log.serialize()}


def _get_logs(node, count, auth):
    """

    :param Node node:
    :param int count:
    :param auth:
    :return list: List of serialized logs

    """
    logs = []

    for log in reversed(node.logs):
        if log and log.node.can_view(auth):
            logs.append(log.serialize())
        if len(logs) >= count:
            break

    return logs

@collect_auth
@must_be_valid_project
def get_logs(**kwargs):
    """

    """
    auth = kwargs['auth']
    node_to_use = kwargs['node'] or kwargs['project']

    if not node_to_use.can_view(auth):
        raise HTTPError(http.FORBIDDEN)
    if 'count' in request.args:
        count = int(request.args['count'])
    elif 'count' in kwargs:
        count = kwargs['count']
    elif request.json and 'count' in request.json.keys():
        count = request.json['count']
    else:
        count = 10

    # Serialize up to `count` logs in reverse chronological order; skip
    # logs that the current user / API key cannot access
    logs = _get_logs(node_to_use, count, auth)
    return {'logs': logs}
