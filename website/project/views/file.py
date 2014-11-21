"""
Files views.
"""
import os
import codecs

from flask import request

from framework.render.tasks import ensure_path, build_rendered_html

from website.util import rubeus
from website.project.decorators import must_be_contributor_or_public
from website import settings
from website.project.views.node import _view_project


@must_be_contributor_or_public
def collect_file_trees(**kwargs):
    """Collect file trees for all add-ons implementing HGrid views, then
    format data as appropriate.
    """
    node = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']

    serialized = _view_project(node, auth, primary=True)
    # Add addon static assets
    serialized.update(rubeus.collect_addon_assets(node))
    return serialized

@must_be_contributor_or_public
def grid_data(**kwargs):
    """View that returns the formatted data for rubeus.js/hgrid
    """
    node = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']
    data = request.args.to_dict()
    return {'data': rubeus.to_hgrid(node, auth, **data)}

# File rendering
def get_cache_path(node_settings, cache_type):
    if cache_type == 'temp':
        base_path = settings.MFR_TEMP_PATH
    elif cache_type == 'rendered':
        base_path = settings.MFR_CACHE_PATH
    else:
        raise ValueError('Argument "cache_type" must be "temp" or "rendered"')
    return os.path.join(
        base_path,
        node_settings.config.short_name,
        node_settings.owner._id,
    )


def get_cache_content(node_settings, cache_file_name, start_render=False,
                      file_content=None, download_url=None):
    """
    """
    cache_dir = get_cache_path(node_settings, cache_type='rendered')
    cache_file_path = os.path.join(cache_dir, cache_file_name)
    try:
        return codecs.open(cache_file_path, 'r', 'utf-8').read()
    except IOError:
        # Start rendering job if requested
        if start_render:
            if file_content is None:
                raise ValueError('Must provide "file_content"')
            temp_file_dir = get_cache_path(node_settings, cache_type='temp')
            temp_file_path = os.path.join(temp_file_dir, cache_file_name)
            ensure_path(temp_file_dir)
            with open(temp_file_path, 'wb') as fp:
                fp.write(file_content)
            build_rendered_html(
                temp_file_path,
                cache_dir,
                cache_file_name,
                download_url,
            )
        return None


def prepare_file(file):

    name = file.filename or settings.MISSING_FILE_NAME
    content = file.read()
    content_type = file.content_type
    file.seek(0, os.SEEK_END)
    size = file.tell()

    return name, content, content_type, size
