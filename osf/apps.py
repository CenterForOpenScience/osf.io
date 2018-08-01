

from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    name = 'osf'
    app_label = 'osf'
    managed = True
