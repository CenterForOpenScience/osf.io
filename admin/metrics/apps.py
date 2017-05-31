from __future__ import unicode_literals

from django.apps import AppConfig as BaseAppConfig


class MetricsAdminAppConfig(BaseAppConfig):
    name = 'admin.metrics'
    label = 'admin_metrics'
