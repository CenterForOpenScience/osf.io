# -*- coding: utf-8 -*-
"""Utility functions for the Google Drive add-on.
"""
import os
from urllib import quote


def build_googledrive_urls(item, node, path):
    return {
        'fetch': node.api_url_for('googledrive_folder_list', folderId=item['id']),
        'folders': node.api_url_for('googledrive_folder_list', folderId=item['id'], path=path),
    }

def to_hgrid(item, node, path):
    """
    :param item: contents returned from Google Drive API
    :return: results formatted as required for Hgrid display
    """
    # quote fails on unicode objects with unicode characters
    # covert to str with .encode('utf-8')
    safe_name = quote(item['title'].encode('utf-8'), safe='')
    path = os.path.join(path, safe_name)

    serialized = {
        'path': path,
        'id': item['id'],
        'kind': 'folder',
        'name': safe_name,
        'addon': 'googledrive',
        'urls': build_googledrive_urls(item, node, path=path)
    }
    return serialized
