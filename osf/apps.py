from __future__ import unicode_literals

from django.apps import AppConfig as BaseAppConfig
from django.db.models.signals import post_migrate
from osf.migrations import add_registration_schemas, update_permission_groups


class AppConfig(BaseAppConfig):
    name = 'osf'
    app_label = 'osf'
    managed = True

    def ready(self):
        super(AppConfig, self).ready()
        post_migrate.connect(
            update_permission_groups,
            dispatch_uid='osf.apps.update_permissions_groups'
        )
        post_migrate.connect(
            add_registration_schemas,
            dispatch_uid='osf.apps.add_registration_schemas'
        )
