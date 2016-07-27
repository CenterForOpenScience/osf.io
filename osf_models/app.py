from __future__ import unicode_literals

from django.apps import AppConfig


class ModelsConfig(AppConfig):
    name = 'osf_models'
    app_label = 'osf_models'
    managed = True

    # DEFINE YOUR OWN  APP SPECIFIC SETTINGS HERE
    # Django likes it's app specific settings snake_case
    try:
        from website import settings as website_settings

        domain = website_settings.DOMAIN
    except:
        domain = 'localhost:5000'
    try:
        from website import settings as website_settings
        api_domain = website_settings.API_DOMAIN
    except:
        api_domain = 'localhost:8000'

    try:
        from api.base import settings as api_settings
        api_base = api_settings.API_BASE
    except ImportError:
        api_base = '/v2/'

