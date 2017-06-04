from __future__ import unicode_literals

from django.apps import AppConfig as BaseAppConfig


class BaseAdminAppConfig(BaseAppConfig):
    name = 'admin.base'
    label = 'admin_base'
