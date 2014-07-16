# -*- coding: utf-8 -*-
import httplib as http
import logging

from framework import request
from framework.auth import Auth, get_current_user, get_api_key, get_current_node
from framework.auth.decorators import collect_auth
from framework.exceptions import HTTPError

from website.project.model import NodeLog, has_anonymous_link
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


def _get_logs(node, count, auth, anonymous=False, offset=0):
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
        # A number of errors due to database inconsistency can arise here. The
        # log can be None; its `node__logged` back-ref can be empty, and the
        # 0th logged node can be None. Catch and log these errors and ignore
        # the offending logs.
        try:
            can_view = log.node__logged[0].can_view(auth)
        except (AttributeError, IndexError) as error:
            logger.exception(error)
            continue
        if can_view:
            if len(logs) < count:
                logs.append(log.serialize(anonymous))
            else:
                has_more_logs = True
                break
    return logs, has_more_logs


@collect_auth
@must_be_valid_project
def get_logs(auth, **kwargs):
    """

    """
    node = kwargs['node'] or kwargs['project']
    page_num = int(request.args.get('pageNum', '').strip('/') or 0)
    link = auth.private_key or request.args.get('view_only', '').strip('/')
    anonymous = has_anonymous_link(node, link)

    if not node.can_view(auth):
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
    logs, has_more_logs = _get_logs(node, count, auth, anonymous,offset)
    return {'logs': logs, 'has_more_logs': has_more_logs}
