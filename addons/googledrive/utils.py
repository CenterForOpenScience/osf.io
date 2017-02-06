# -*- coding: utf-8 -*-
"""Utility functions for the Google Drive add-on.
"""
import os
from urllib import quote

from website.util import api_v2_url

def build_googledrive_urls(item, node, path):
    return {
        'fetch': api_v2_url('nodes/{}/addons/googledrive/folders/'.format(node._id), params={'path': path}),
        'folders': api_v2_url('nodes/{}/addons/googledrive/folders/'.format(node._id), params={'path': path, 'id': item['id']})
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
