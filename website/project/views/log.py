# -*- coding: utf-8 -*-
import httplib as http
import logging
import math
from itertools import islice

from flask import request

from framework.exceptions import HTTPError
from framework.auth.decorators import collect_auth
from framework.transactions.handlers import no_auto_transaction


from website.views import serialize_log
from website.project.model import NodeLog
from website.project.model import has_anonymous_link
from website.project.decorators import must_be_valid_project

logger = logging.getLogger(__name__)


@collect_auth
@no_auto_transaction
def get_log(auth, log_id):

    log = NodeLog.load(log_id)
    node_to_use = log.node

    if not node_to_use.can_view(auth):
        raise HTTPError(http.FORBIDDEN)

    return {'log': serialize_log(log)}


def _get_logs(node, count, auth, link=None, start=0):
    """

    :param Node node:
    :param int count:
    :param auth:
    :return list: List of serialized logs,
            boolean: if there are more logs

    """
    logs = []
    total = 0

    for log in reversed(node.logs):
        # A number of errors due to database inconsistency can arise here. The
        # log can be None; its `node__logged` back-ref can be empty, and the
        # 0th logged node can be None. Catch and log these errors and ignore
        # the offending logs.
        log_node = log.resolve_node(node)
        if log.can_view(node, auth):
            total += 1
            anonymous = has_anonymous_link(log_node, auth)
            logs.append(serialize_log(log, anonymous))

    pages = math.ceil(total / float(count))

    return [log for log in islice(logs, start, start + count)], total, pages


@no_auto_transaction
@collect_auth
@must_be_valid_project
def get_logs(auth, **kwargs):
    """

    """
    node = kwargs['node'] or kwargs['project']
    page = int(request.args.get('page', 0))
    link = auth.private_key or request.args.get('view_only', '').strip('/')

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
    start = page * count

    # Serialize up to `count` logs in reverse chronological order; skip
    # logs that the current user / API key cannot access
    logs, total, pages = _get_logs(node, count, auth, link, start)
    return {'logs': logs, 'total': total, 'pages': pages, 'page': page}
