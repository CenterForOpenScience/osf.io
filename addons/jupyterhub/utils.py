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
