"""
Utility functions for JupyterHub add-on.
"""


def serialize_jupyterhub_widget(node):
    jupyterhub = node.get_addon('jupyterhub')
    ret = {
        'complete': True,
        'include': False,
    }
    ret.update(jupyterhub.config.to_json())
    return ret


def get_jupyterhub_import_url(node, base_url):
    if not base_url.endswith('/'):
        base_url += '/'
    return base_url + node._id
