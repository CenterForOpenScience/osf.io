# -*- coding: utf-8 -*-
import os
import logging

from website.project.utils import get_cache_content
from website.util import rubeus
from website.addons.dropbox.client import get_node_addon_client

logger = logging.getLogger(__name__)
debug = logger.debug

def get_file_name(path):
    """Given a path, get just the base filename.
    Handles "/foo/bar/baz.txt/" -> "baz.txt"
    """
    return os.path.basename(path.strip('/'))


def clean_path(path):
    """Ensure a path is formatted correctly for url_for."""
    return path.strip('/')


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


def ensure_leading_slash(path):
    if not path.startswith('/'):
        return '/' + path
    return path


def build_dropbox_urls(item, node):
    path = clean_path(item['path'])  # Strip trailing and leading slashes
    if item['is_dir']:
        return {
            'upload': node.api_url_for('dropbox_upload', path=path),
            'fetch':  node.api_url_for('dropbox_hgrid_data_contents', path=path)
        }
    else:
        return {
            'download': node.web_url_for('dropbox_download', path=path),
            'view': node.web_url_for('dropbox_view_file', path=path),
            'delete': node.api_url_for('dropbox_delete_file', path=path)
        }


def metadata_to_hgrid(item, node, permissions):
    filename = get_file_name(item['path'])
    serialized = {
        'addon': 'dropbox',
        'permissions': permissions,
        'name': get_file_name(item['path']),
        'ext': os.path.splitext(filename)[1],
        rubeus.KIND: rubeus.FOLDER if item['is_dir'] else rubeus.FILE,
        'urls': build_dropbox_urls(item, node),
    }
    return serialized


# TODO(sloria): TEST ME
def list_dropbox_files(node, files=None, cursor=None, client=None):
    node_settings = node.get_addon('dropbox')
    client = client or get_node_addon_client(node_settings)

    if files is None:
        files = {}

    has_more = True

    if node_settings.folder:
        path_prefix = ensure_leading_slash(node_settings.folder)
    else:
        path_prefix = None

    while has_more:
        result = client.delta(cursor, path_prefix=path_prefix)
        cursor = result['cursor']
        has_more = result['has_more']

        for lowercase_path, metadata in result['entries']:

            if metadata is not None:
                files[lowercase_path] = metadata

            else:
                # no metadata indicates a deletion

                # remove if present
                files.pop(lowercase_path, None)

                # in case this was a directory, delete everything under it
                for other in files.keys():
                    if other.startswith(lowercase_path + '/'):
                        del files[other]

    return files, cursor
