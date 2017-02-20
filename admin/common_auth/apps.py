from __future__ import unicode_literals

from django.apps import AppConfig as BaseAppConfig


class CommonAuthAdminAppConfig(BaseAppConfig):
    name = 'admin.common_auth'
    label = 'admin_common_auth'
