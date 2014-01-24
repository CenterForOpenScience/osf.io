"""

"""

import json

from framework.flask import request
from framework.auth import get_current_user

from website.project.decorators import must_be_contributor_or_public
from website.project.views.node import _view_project


def _get_dummy_container(node, user, link='', parent=None):
    """Create HGrid JSON for a dummy component container.

    :return dict: HGrid-formatted dummy container

    """
    can_view = node.can_view(user, link)
    return {
        'uid': 'node:{0}'.format(node._id),
        'parent_uid': parent if parent else 'null',
        'name': 'Component: {0}'.format(node.title)
            if can_view
            else 'Private Component',
        'type': 'folder',
        'can_edit': node.can_edit(user) if can_view else False,
        'can_view': can_view,
        # Can never drag into component dummy folder
        'permission': False,
        'lazyLoad': node.api_url + 'files/',
    }


def _collect_file_trees(node, user, link='', parent='null', **kwargs):
    """Collect file trees for all add-ons implementing HGrid views. Create
    dummy containers for each child of the target node, and for each add-on
    implementing HGrid views.

    :return list: List of HGrid-formatted file trees

    """
    grid_data = []

    # Collect add-on file trees
    for addon in node.get_addons():
        if addon.config.has_hgrid_files:
            dummy = addon.config.get_hgrid_dummy(
                addon, user, parent, **kwargs
            )
            dummy['iconUrl'] = addon.config.icon_url
            # Skip if dummy folder is falsy
            if dummy:
                grid_data.append(dummy)

    # Collect component file trees
    for child in node.nodes:
        container = _get_dummy_container(child, user, link, parent)
        grid_data.append(container)

    return grid_data


def _collect_tree_js(node):
    """Collect JavaScript includes for all add-ons implementing HGrid views.

    :return list: List of JavaScript include paths

    """
    scripts = []
    for addon in node.get_addons():
        scripts.extend(addon.config.include_js.get('files', []))
    return scripts


@must_be_contributor_or_public
def collect_file_trees(*args, **kwargs):
    """Collect file trees for all add-ons implementing HGrid views, then
    format data as appropriate.

    """
    link = kwargs['link']
    node = kwargs['node'] or kwargs['project']
    mode = kwargs.get('mode')
    user = get_current_user()
    data = request.args.to_dict()

    grid_data = _collect_file_trees(node, user, link, **data)
    if mode == 'page':
        rv = _view_project(node, user, link)
        rv.update({
            'grid_data': json.dumps(grid_data),
            'tree_js': _collect_tree_js(node),
        })
        return rv
    elif mode == 'widget':
        return {'grid_data': grid_data}
    else:
        return grid_data