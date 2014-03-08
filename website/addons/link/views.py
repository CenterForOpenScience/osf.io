"""

"""

from framework import request
from website.project import decorators
from website.project.views.node import _view_project


@decorators.must_have_permission('write')
@decorators.must_have_addon('link', 'node')
def link_set_config(*args, **kwargs):
    # TODO: Validate
    link = kwargs['node_addon']
    link.link_url = request.json.get('link_url', '')
    link.save()


@decorators.must_be_contributor_or_public
@decorators.must_have_addon('link', 'node')
def link_widget(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    link = node.get_addon('link')

    rv = {
        'complete': True,
        'link_url': link.link_url,
    }
    rv.update(link.config.to_json())
    return rv

@decorators.must_be_contributor_or_public
def link_page(**kwargs):

    user = kwargs['auth'].user
    node = kwargs['node'] or kwargs['project']
    link = node.get_addon('link')

    data = _view_project(node, user)

    rv = {
        'complete': True,
        'link_url': link.link_url,
    }
    rv.update(data)
    return rv
