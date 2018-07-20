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

def serialize_forward_widget(node):
    node_addon = node.get_addon('forward')
    forward_widget_data = serialize_settings(node_addon)
    forward_widget_data['complete'] = settings_complete(node_addon)
    forward_widget_data.update(node_addon.config.to_json())
    return forward_widget_data
