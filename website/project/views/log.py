# -*- coding: utf-8 -*-
import httplib as http
import logging

from flask import request

from framework.exceptions import HTTPError
from framework.auth.decorators import collect_auth
from framework.transactions.handlers import no_auto_transaction


from website.views import serialize_log, paginate
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


def _get_logs(node, count, auth, link=None, page=0):
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
        # 0th logged node can be None. Need to make sure that log is not None
        if log:
            log_node = log.resolve_node(node)
            if log.can_view(node, auth):
                total += 1
                anonymous = has_anonymous_link(log_node, auth)
                logs.append(serialize_log(log, anonymous))
        else:
            logger.warn('Log on node {} is None'.format(node._id))

    paginated_logs, pages = paginate(logs, total, page, count)

    return list(paginated_logs), total, pages


@no_auto_transaction
@collect_auth
@must_be_valid_project
def get_logs(auth, **kwargs):
    """

    """
    node = kwargs['node'] or kwargs['project']
    try:
        page = int(request.args.get('page', 0))
    except ValueError:
        raise HTTPError(http.BAD_REQUEST, data=dict(
            message_long='Invalid value for "page".'
        ))
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

    # Serialize up to `count` logs in reverse chronological order; skip
    # logs that the current user / API key cannot access
    logs, total, pages = _get_logs(node, count, auth, link, page)
    return {'logs': logs, 'total': total, 'pages': pages, 'page': page}
