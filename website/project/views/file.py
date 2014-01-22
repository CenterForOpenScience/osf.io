"""

"""

import json

from framework.flask import request
from framework.auth import get_current_user

from website.project.decorators import must_be_contributor_or_public
from website.project.views.node import _view_project


def _get_dummy_container(node, user, parent=None):
    return {
        'uid': 'node:{0}'.format(node._id),
        'parent_uid': parent if parent else 'null',
        'name': 'Component: {0}'.format(node.title),
        'type': 'folder',
        'can_edit': node.can_edit(user),
        'lazyLoad': node.api_url + 'files/',
    }


def _collect_file_trees(node, user, parent='null', **kwargs):

    grid_data = []

    for addon in node.get_addons():
        if addon.config.get_hgrid_dummy:
            grid_data.append(
                addon.config.get_hgrid_dummy(
                    addon, user, parent, **kwargs
                )
            )

    for child in node.nodes:
        if child.can_view(user):
            container = _get_dummy_container(child, user, parent)
            grid_data.append(container)

    return grid_data


@must_be_contributor_or_public
def collect_file_trees(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    user = get_current_user()
    data = request.args.to_dict()

    parent = data.pop('parent', 'null')

    return _collect_file_trees(node, user, parent, **data)


@must_be_contributor_or_public
def show_file_trees(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    user = get_current_user()
    data = dict(request.args)

    rv = _view_project(node, user)
    rv['grid_data'] = json.dumps(
        _collect_file_trees(node, user, **data)
    )

    return rv
