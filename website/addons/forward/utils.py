
def serialize_settings(node_addon):
    return {
        'url': node_addon.url,
        'redirectBool': node_addon.redirect_bool,
        'redirectSecs': node_addon.redirect_secs,
    }


def settings_complete(node_addon):
    return bool(
        node_addon.url
        and node_addon.redirect_bool
        and node_addon.redirect_secs
    )
