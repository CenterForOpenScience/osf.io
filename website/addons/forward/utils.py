"""
Utility functions for Forward add-on.
"""


def serialize_settings(node_addon):
    return {
        'url': node_addon.url,
        'label': node_addon.label,
        'redirectBool': node_addon.redirect_bool
    }


def settings_complete(node_addon):
    return (
        node_addon.url is not None
        and node_addon.redirect_bool is not None
    )
