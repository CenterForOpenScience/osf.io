

from django.apps import AppConfig as BaseAppConfig


class BaseAdminAppConfig(BaseAppConfig):
    name = 'admin.base'
    label = 'admin_base'
