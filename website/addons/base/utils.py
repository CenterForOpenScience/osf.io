from os.path import basename

def serialize_addon_config(config):
    lookup = config.template_lookup

    return {
        'addon_short_name': config.short_name,
        'addon_full_name': config.full_name,
        'node_settings_template': lookup.get_template(basename(config.node_settings_template)),
        'user_settings_template': lookup.get_template(basename(config.user_settings_template)),
    }
