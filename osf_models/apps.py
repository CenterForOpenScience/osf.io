from __future__ import unicode_literals

from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    name = 'osf_models'
    app_label = 'osf_models'
    managed = True

    # DEFINE YOUR OWN  APP SPECIFIC SETTINGS HERE
    # Django likes it's app specific settings snake_case
    try:
        from website import settings as website_settings
    except ImportError:
        domain = 'localhost:5000'
        email_token_expiration = 24
    else:
        domain = website_settings.DOMAIN
        email_token_expiration = website_settings.EMAIL_TOKEN_EXPIRATION

    try:
        from website import settings as website_settings
    except ImportError:
        api_domain = 'localhost:8000'
    else:
        api_domain = website_settings.API_DOMAIN

    try:
        from api.base import settings as api_settings
    except ImportError:
        api_base = '/v2/'
    else:
        api_base = api_settings.API_BASE
