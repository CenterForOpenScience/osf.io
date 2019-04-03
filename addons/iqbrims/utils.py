# -*- coding: utf-8 -*-
"""Utility functions for the IQB-RIMS add-on.
"""
import os

from website.util import api_v2_url

def build_iqbrims_urls(item, node, path):
    return {
        'fetch': api_v2_url('nodes/{}/addons/iqbrims/folders/'.format(node._id), params={'path': path}),
        'folders': api_v2_url('nodes/{}/addons/iqbrims/folders/'.format(node._id), params={'path': path, 'id': item['id']})
    }

def to_hgrid(item, node, path):
    """
    :param item: contents returned from IQB-RIMS API
    :return: results formatted as required for Hgrid display
    """
    path = os.path.join(path, item['title'])

    serialized = {
        'path': path,
        'id': item['id'],
        'kind': 'folder',
        'name': item['title'],
        'addon': 'iqbrims',
        'urls': build_iqbrims_urls(item, node, path=path)
    }
    return serialized
