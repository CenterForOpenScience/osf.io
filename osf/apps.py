from __future__ import unicode_literals

from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    name = 'osf'
    app_label = 'osf'
    managed = True
