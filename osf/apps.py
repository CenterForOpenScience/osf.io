import logging
from django.apps import AppConfig as BaseAppConfig
from django.db.models.signals import post_migrate
from osf.migrations import update_permission_groups, update_subjects
from osf.migrations import (
    update_permission_groups,
    update_waffle_flags,
    create_cache_table,
    update_license
)

logger = logging.getLogger(__file__)


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
            update_subjects,
            dispatch_uid='osf.apps.update_subjects'
        )
        post_migrate.connect(
            update_license,
            dispatch_uid='osf.apps.ensure_licenses',
        )
        post_migrate.connect(
            update_waffle_flags,
            dispatch_uid='osf.apps.update_waffle_flags'
        )
        post_migrate.connect(
            create_cache_table,
            dispatch_uid='osf.apps.create_cache_table'
        )
