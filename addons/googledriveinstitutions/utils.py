# -*- coding: utf-8 -*-
"""Utility functions for the Google Drive in G Suite / Google Workspace add-on.
"""
import os

from website.util import api_v2_url

def build_googledriveinstitutions_urls(item, node, path):
    return {
        'fetch': api_v2_url('nodes/{}/addons/googledriveinstitutions/folders/'.format(node._id), params={'path': path}),
        'folders': api_v2_url('nodes/{}/addons/googledriveinstitutions/folders/'.format(node._id), params={'path': path, 'id': item['id']})
    }

def to_hgrid(item, node, path):
    """
    :param item: contents returned from Google Drive API
    :return: results formatted as required for Hgrid display
    """
    path = os.path.join(path, item['name'])

    serialized = {
        'path': path,
        'id': item['id'],
        'kind': 'folder',
        'name': item['name'],
        'addon': 'googledriveinstitutions',
        'urls': build_googledriveinstitutions_urls(item, node, path=path)
    }
    return serialized
