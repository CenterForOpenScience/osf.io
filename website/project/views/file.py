"""

"""

import os
import json
import codecs

from framework.flask import request

from framework.render.tasks import build_rendered_html
from website.project.decorators import must_be_contributor_or_public
from website.project.views.node import _view_project
from website import settings


def _get_dummy_container(node, auth, parent=None):
    """Create HGrid JSON for a dummy component container.

    :return dict: HGrid-formatted dummy container

    """
    can_view = node.can_view(auth)
    return {
        'uid': 'node:{0}'.format(node._id),
        'parent_uid': parent if parent else 'null',
        'name': 'Component: {0}'.format(node.title)
            if can_view
            else 'Private Component',
        'type': 'folder',
        'can_edit': node.can_edit(auth) if can_view else False,
        'can_view': can_view,
        # Can never drag into component dummy folder
        'permission': False,
        'lazyLoad': node.api_url + 'files/',
    }


def _collect_file_trees(node, auth, parent='null', visited=None, **kwargs):
    """Collect file trees for all add-ons implementing HGrid views. Create
    dummy containers for each child of the target node, and for each add-on
    implementing HGrid views.

    :param Auth auth: Consolidated authorization
    :param visited: List of visited nodes; use to avoid circular references
    :return: List of HGrid-formatted file trees

    """
    grid_data = []
    visited = visited or []

    # Collect add-on file trees
    for addon in node.get_addons():
        if addon.config.has_hgrid_files:
            dummy = addon.config.get_hgrid_dummy(
                addon, auth, parent, **kwargs
            )
            # Skip if dummy folder is falsy
            if dummy:
                # Add add-on icon URL if specified
                dummy['iconUrl'] = addon.config.icon_url
                grid_data.append(dummy)

    # Collect component file trees
    for child in node.nodes:
        if not child.is_deleted and child not in visited:
            container = _get_dummy_container(child, auth, parent)
            grid_data.append(container)
            visited.append(child)

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
    node = kwargs['node'] or kwargs['project']
    mode = kwargs.get('mode')
    auth = kwargs['auth']
    data = request.args.to_dict()

    grid_data = _collect_file_trees(node, auth, **data)
    if mode == 'page':
        rv = _view_project(node, auth)
        rv.update({
            'grid_data': json.dumps(grid_data),
            'tree_js': _collect_tree_js(node),
        })
        return rv
    elif mode == 'widget':
        return {'grid_data': grid_data}
    else:
        return grid_data

# File rendering

def get_cache_path(node_settings):
    return os.path.join(
        settings.MFR_CACHE_PATH,
        node_settings.config.short_name,
        node_settings.owner._id,
    )


def get_cache_content(node_settings, cache_file, start_render=False,
                      file_path=None, file_content=None, download_path=None):
    """

    """
    # Get rendered content if present
    cache_path = get_cache_path(node_settings)
    cache_file_path = os.path.join(cache_path, cache_file)
    try:
        return codecs.open(cache_file_path, 'r', 'utf-8').read()
    except IOError:
        # Start rendering job if requested
        if start_render:
            build_rendered_html(
                file_path, file_content, cache_path, cache_file_path,
                download_path
            )
        return None
