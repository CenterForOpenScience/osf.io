# -*- coding: utf-8 -*-
"""Utility functions for the Google Drive add-on.
"""
import os
from urllib import quote

from api.base.utils import absolute_reverse

def build_googledrive_urls(item, node, path):
    return {
        'fetch': absolute_reverse('nodes:node-addon-folders', kwargs={'node_id': node._id, 'provider': 'googledrive'}, query_kwargs={'path': path}),
        'folders': absolute_reverse('nodes:node-addon-folders', kwargs={'node_id': node._id, 'provider': 'googledrive'}, query_kwargs={'path': path, 'id': item['id']}),
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
        'provider': 'googledrive',  # TODO: remove duplication -- APIv2
        'urls': build_googledrive_urls(item, node, path=path)
    }
    return serialized
