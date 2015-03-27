import os

def get_default_templates(base_path):
    NODE_SETTINGS_TEMPLATE_DEFAULT = os.path.join(
        base_path,
        'project',
        'addon',
        'node_settings_default.mako',
    )

    USER_SETTINGS_TEMPLATE_DEFAULT = os.path.join(
        base_path,
        'project',
        'addon',
        'user_settings_default.mako',
    )
    return NODE_SETTINGS_TEMPLATE_DEFAULT, USER_SETTINGS_TEMPLATE_DEFAULT
