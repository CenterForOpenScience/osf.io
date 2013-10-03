# todo: move routing to new style

import framework


def _rescale_ratio(nodes):
    """

    :param nodes:
    :return:
    """
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
        'url' : node.url(),
        'api_url' : node.api_url(),
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
    nodes = [
        node
        for node in user.node__contributed
        if node.category == 'project'
        and not node.is_deleted
        and not node.is_registration
    ]
    node_json = [
        {
            'api_url' : node.api_url(),
        }
        for node in nodes
    ]

    print 'HIHIHI', _rescale_ratio(nodes)
    return {
        'nodes' : node_json,
        'rescale_ratio' : _rescale_ratio(nodes),
    }

@framework.get('/about/')
def about():
    return framework.render(filename="about.mako")

@framework.get('/howosfworks/')
def howosfworks():
    return framework.render(filename="howosfworks.mako")

@framework.get('/reproducibility/')
def reproducibility():
    return framework.redirect('/project/EZcUj/wiki')

@framework.get('/faq/')
def faq():
    return framework.render(filename="faq.mako")

@framework.get('/getting-started/')
def getting_started():
    return framework.render(filename="getting_started.mako")

@framework.get('/explore/')
def explore():
    return framework.render(filename="explore.mako")

@framework.get('/messages/')
@framework.get('/help/')
def soon():
    return framework.render(filename="comingsoon.mako")