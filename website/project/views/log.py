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


def _get_logs(node, count, auth, offset=0):

    """
    :param Node node:
    :param int count:
    :param auth:
    :return list: List of serialized logs,
            boolean: if there are more logs

    """
    logs = []
    has_more_logs = False
    for log in (x for idx, x in enumerate(reversed(node.logs)) if idx >= offset):
        if log and log.node__logged and log.node__logged[0].can_view(auth):
            if len(logs) < count:
                logs.append(log.serialize())
            else:
                has_more_logs =True
                break
    return logs, has_more_logs

@collect_auth
@must_be_valid_project
def get_logs(**kwargs):
    """

    """
    auth = kwargs['auth']
    node_to_use = kwargs['node'] or kwargs['project']
    page_num = int(request.args.get('pageNum', '').strip('/') or 0)

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
    offset = page_num*count

    # Serialize up to `count` logs in reverse chronological order; skip
    # logs that the current user / API key cannot access
    logs, has_more_logs = _get_logs(node_to_use, count, auth, offset)
    return {'logs': logs, 'has_more_logs': has_more_logs}

