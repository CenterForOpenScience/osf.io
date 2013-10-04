# todo: move routing to new style

import framework
from framework import redirect, Q

def _rescale_ratio(nodes):
    """

    :param nodes:
    :return:
    """
    if not nodes:
        return 0
    return float(max([
        len(node.logs)
        for node in nodes
    ]))


def _render_node(node):
    """

    :param node:
    :return:
    """
    return {
        'id' : node._primary_key,
        'url' : node.url,
        'api_url' : node.api_url,
    }


def _render_nodes(nodes):
    """

    :param nodes:
    :return:
    """

    return {
        'nodes' : [
            _render_node(node)
            for node in nodes
        ],
        'rescale_ratio' : _rescale_ratio(nodes),
    }


@framework.must_be_logged_in
def dashboard(*args, **kwargs):
    user = kwargs['user']
    nodes = user.node__contributed.find(
        Q('category', 'eq', 'project') &
        Q('is_deleted', 'eq', False) &
        Q('is_registration', 'eq', False)
    )
    recent_log_ids = list(user.get_recent_log_ids())

    rv = _render_nodes(nodes)
    rv['logs'] = recent_log_ids
    return rv

def reproducibility():
    return framework.redirect('/project/EZcUj/wiki')
