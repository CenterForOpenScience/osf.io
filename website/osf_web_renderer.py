import framework
from framework import WebRenderer
from website import settings, language, util
from website.assets import env as assets_env, env

__author__ = 'jwshephe'


def get_globals():
    """Context variables that are available for every template rendered by
    OSFWebRenderer.

    """
    user = framework.auth.get_current_user()
    return {
        'user_name': user.username if user else '',
        'user_full_name': user.fullname if user else '',
        'user_id': user._primary_key if user else '',
        'user_url': user.url if user else '',
        'user_api_url': user.api_url if user else '',
        'display_name': framework.auth.get_display_name(user.username) if user else '',
        'use_cdn': settings.USE_CDN_FOR_CLIENT_LIBS,
        'piwik_host': settings.PIWIK_HOST,
        'piwik_site_id': settings.PIWIK_SITE_ID,
        'dev_mode': settings.DEV_MODE,
        'allow_login': settings.ALLOW_LOGIN,
        'status': framework.status.pop_status_messages(),
        'js_all': assets_env['js'].urls(),
        'css_all': assets_env['css'].urls(),
        'js_bottom': assets_env['js_bottom'].urls(),
        'domain': settings.DOMAIN,
        'language': language,
        'web_url_for': util.web_url_for,
        'api_url_for': util.api_url_for,
    }


class OsfWebRenderer(WebRenderer):

    def __init__(self, *args, **kwargs):
        kwargs['data'] = get_globals
        super(OsfWebRenderer, self).__init__(*args, **kwargs)

