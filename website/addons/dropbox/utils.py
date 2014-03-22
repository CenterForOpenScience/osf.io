# -*- coding: utf-8 -*-
import os
from website.project.utils import get_cache_content

from website.addons.dropbox.client import get_node_addon_client


def get_file_name(path):
    """Given a path, get just the base filename.
    Handles "/foo/bar/baz.txt/" -> "baz.txt"
    """
    return os.path.basename(path.strip('/'))


# TODO(sloria): TEST ME
def render_dropbox_file(file_obj, client=None):
    # Filename for the cached MFR HTML file
    cache_name = file_obj.get_cache_filename(client=client)
    node_settings = file_obj.node.get_addon('dropbox')
    rendered = get_cache_content(node_settings, cache_name)
    if rendered is None:  # not in MFR cache
        dropbox_client = client or get_node_addon_client(node_settings)
        file_response, metadata = dropbox_client.get_file_and_metadata(file_obj.path)
        rendered = get_cache_content(
            node_settings=node_settings,
            cache_file=cache_name,
            start_render=True,
            file_path=get_file_name(file_obj.path),
            file_content=file_response.read(),
            download_path=file_obj.download_url
        )
    return rendered
