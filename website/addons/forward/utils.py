"""
Utility functions for Forward add-on.
"""


def serialize_settings(node_addon):
    return {
        'url': node_addon.url,
        'label': node_addon.label,
    }


def settings_complete(node_addon):
    return (
        node_addon.url is not None
    )
