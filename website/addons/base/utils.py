from os.path import basename

from website import settings

def serialize_addon_config(config):
    lookup = config.template_lookup

    return {
        'addon_short_name': config.short_name,
        'addon_full_name': config.full_name,
        'node_settings_template': lookup.get_template(basename(config.node_settings_template)),
        'user_settings_template': lookup.get_template(basename(config.user_settings_template)),
    }

def get_addons_by_config_type(config_type, user):
    addons = [addon for addon in settings.ADDONS_AVAILABLE if config_type in addon.configs]
    addon_settings = []    
    for addon_config in sorted(addons, key=lambda cfg: cfg.full_name.lower()):
        short_name = addon_config.short_name
        config = serialize_addon_config(addon_config)
        user_settings = user.get_addon(short_name)
        if user_settings:
            user_settings = user_settings.to_json()
        config.update({
            'user_settings': user_settings,
        })
        addon_settings.append(config)
    return addon_settings
