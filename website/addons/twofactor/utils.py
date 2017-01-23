from website.util import api_url_for

def serialize_urls(user_addon):
    return {
        'enable': api_url_for('twofactor_enable'),
        'disable': api_url_for('twofactor_disable'),
        'settings': api_url_for('twofactor_settings_put'),
        'otpauth': user_addon.otpauth_url if user_addon else '',
    }

def serialize_settings(auth):
    user_addon = auth.user.get_addon('twofactor')
    result = {}
    if user_addon:
        result = user_addon.to_json(auth.user)
    else:
        result = {
            'is_enabled': False,
            'is_confirmed': False,
            'secret': None,
            'drift': None,
        }
    urls = serialize_urls(user_addon)
    result.update({'urls': urls})
    return result
