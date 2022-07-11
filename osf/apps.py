import logging
from django.apps import AppConfig as BaseAppConfig
from django.db.models.signals import post_migrate

logger = logging.getLogger(__file__)
from osf.migrations import (
    update_waffle_flags,
    update_permission_groups,
    update_storage_regions,
    update_blocked_email_domains,
    update_subjects,
    update_default_providers
)


class AppConfig(BaseAppConfig):
    name = 'osf'
    app_label = 'osf'
    managed = True

    def ready(self):
        super().ready()
        post_migrate.connect(
            update_permission_groups,
            dispatch_uid='django.contrib.auth.management.create_permissions'  # override default perm groups
        )
        post_migrate.connect(
            update_waffle_flags,
            dispatch_uid='osf.apps.update_waffle_flags'
        )
        post_migrate.connect(
            update_blocked_email_domains,
            dispatch_uid='osf.apps.update_blocked_email_domains',
        )
        post_migrate.connect(
            update_storage_regions,
            dispatch_uid='osf.apps.update_storage_regions',
        )
        post_migrate.connect(
            update_waffle_flags,
            dispatch_uid='osf.apps.update_waffle_flags'
        )
        post_migrate.connect(
            update_subjects,
            dispatch_uid='osf.apps.update_subjects',
        )
        post_migrate.connect(
            update_default_providers,
            dispatch_uid='osf.apps.update_default_providers'
        )
