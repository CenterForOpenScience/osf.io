from os.path import basename

from website import settings

def serialize_addon_config(config, user):
    lookup = config.template_lookup

    user_addon = user.get_addon(config.short_name)
    ret = {
        'addon_short_name': config.short_name,
        'addon_full_name': config.full_name,
        'node_settings_template': lookup.get_template(basename(config.node_settings_template)),
        'user_settings_template': lookup.get_template(basename(config.user_settings_template)),
        'is_enabled': user_addon is not None,
        'addon_icon_url': config.icon_url,
    }
    ret.update(user_addon.to_json(user) if user_addon else {})
    return ret

def get_addons_by_config_type(config_type, user):
    addons = [addon for addon in settings.ADDONS_AVAILABLE if config_type in addon.configs]
    return [serialize_addon_config(addon_config, user) for addon_config in sorted(addons, key=lambda cfg: cfg.full_name.lower())]

def maybe_show_lost_file_metadata(auth, node, file):
    msg = """
    </div>"""  # None is default
    if (auth.user and node.is_contributor(auth.user)) or (auth.private_key and auth.private_key in node.private_link_keys_active):
        last_meta = file.last_known_metadata
        last_seen = last_meta.get('last_seen', None)
        hashes = last_meta.get('hashes', None)
        path = last_meta.get('path', None)
        size = last_meta.get('size', None)
        parts = [
            """This file was """ if last_seen or hashes or path or size else '',
            """last seen on {}""".format(last_seen) if last_seen else '',
            """and found at path {}""".format(path) if last_seen and path else '',
            """last found at path {}""".format(path) if not last_seen and path else '',
            """with a file size of {}""".format(size) if size and (last_seen or path) else '',
            """last seen with a file size of {}""".format(size) if size and not (last_seen or path) else '',
            """.
""" if last_seen or hashes or path or size else '',
            """Hashes of last seen version:
{}""".format(
                '\n'.join(['{}: {}'.format(k, v) for k, v in hashes.items()])
            ) if hashes else '',  # TODO: Format better for UI
            msg
        ]
        return ''.join(parts)
    return msg
