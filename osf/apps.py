import logging

from corsheaders.signals import check_request_enabled
from django.apps import AppConfig as BaseAppConfig
from django.db.models.signals import post_migrate

from api.base.middleware_cors_signal import cors_allow_institution_domains
from osf.migrations import (
    add_registration_schemas,
    create_cache_table,
    update_blocked_email_domains,
    update_license,
    update_permission_groups,
    update_storage_regions,
    update_waffle_flags,
    update_default_providers
)

logger = logging.getLogger(__file__)


class AppConfig(BaseAppConfig):

    name = 'osf'
    app_label = 'osf'
    managed = True

    def ready(self):
        super().ready()

        check_request_enabled.connect(cors_allow_institution_domains)
        post_migrate.connect(
            add_registration_schemas,
            dispatch_uid='osf.apps.add_registration_schemas'
        )

        post_migrate.connect(
            update_permission_groups,
            dispatch_uid='osf.apps.update_permissions_groups'
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

        post_migrate.connect(
            update_default_providers,
            dispatch_uid='osf.apps.update_default_providers'
        )

        post_migrate.connect(
            update_blocked_email_domains,
            dispatch_uid='osf.apps.update_blocked_email_domains'
        )

        post_migrate.connect(
            update_storage_regions,
            dispatch_uid='osf.apps.update_storage_regions'
        )
