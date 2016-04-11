# -*- coding: utf-8 -*-
import httplib as http
import logging
import math

from flask import request

from framework.exceptions import HTTPError
from framework.auth.decorators import collect_auth
from framework.transactions.handlers import no_auto_transaction


from website.views import serialize_log, validate_page_num
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

    return {'log': serialize_log(log, auth=auth)}


def _get_logs(node, count, auth, page=0):
    """

    :param Node node:
    :param int count:
    :param auth:
    :return list: List of serialized logs,
            boolean: if there are more logs

    """
    related_log_actions = [NodeLog.PROJECT_CREATED, NodeLog.NODE_REMOVED,
                           NodeLog.FILE_COPIED, NodeLog.FILE_MOVED,
                           NodeLog.POINTER_CREATED, NodeLog.POINTER_REMOVED]

    logs_set = node.get_aggregate_logs_queryset(auth)
    total = logs_set.count()
    pages = math.ceil(total / float(count))
    validate_page_num(page, pages)

    start = page * count
    stop = start + count

    # TODO: @caseyrollins -- fix this complicated list comprehension?
    logs = [
        serialize_log(log, auth=auth, anonymous=has_anonymous_link(node, auth))
        for log in logs_set[start:stop]
        if log.node == node or log.node.can_view(auth) or (not log.node.can_view(auth) and log.action in related_log_actions)
    ]

    return logs, total, pages

@no_auto_transaction
@collect_auth
@must_be_valid_project(retractions_valid=True)
def get_logs(auth, node, **kwargs):
    """

    """
    try:
        page = int(request.args.get('page', 0))
    except ValueError:
        raise HTTPError(http.BAD_REQUEST, data=dict(
            message_long='Invalid value for "page".'
        ))

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

    # Serialize up to `count` logs in reverse chronological order; skip
    # logs that the current user / API key cannot access
    logs, total, pages = _get_logs(node, count, auth, page)
    return {'logs': logs, 'total': total, 'pages': pages, 'page': page}
