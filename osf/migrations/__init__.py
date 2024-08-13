import sys
import json
import logging

from django.apps import apps
from django.core.management import call_command
from django.db.utils import ProgrammingError

from addons.osfstorage.settings import DEFAULT_REGION_ID, DEFAULT_REGION_NAME
from osf.management.commands.manage_switch_flags import manage_waffle
from osf.utils.migrations import ensure_schemas, map_schemas_to_schemablocks
from website import settings as osf_settings

logger = logging.getLogger(__file__)

OSF_PREPRINTS_PROVIDER_DATA = {
    '_id': 'osf',
    'name': 'Open Science Framework',
    'domain': osf_settings.DOMAIN,
    'share_publish_type': 'Preprint',
    'domain_redirect_enabled': False,
}

OSF_REGISTRIES_PROVIDER_DATA = {
    '_id': 'osf',
    'name': 'OSF Registries',
    'domain': osf_settings.DOMAIN,
    'share_publish_type': 'Registration',
    'domain_redirect_enabled': False,
}


# Admin group permissions
def get_admin_read_permissions():
    from django.contrib.auth.models import Permission
    return Permission.objects.filter(codename__in=[
        'view_brand',
        'view_node',
        'view_registration',
        'view_user',
        'view_conference',
        'view_spam',
        'view_metrics',
        'view_desk',
        'view_osfuser',
        'view_user',
        'view_preprintservice',
        'view_institution',
        'view_institutionassetfile',
        'view_preprintprovider',
        'view_subject',
        'view_scheduledbanner',
        'view_collectionprovider',
        'view_providerassetfile',
        'view_registrationprovider',
        'view_management',
        'view_notabledomain',
        'view_cedarmetadatatemplate',
    ])


def get_admin_write_permissions():
    from django.contrib.auth.models import Permission
    return Permission.objects.filter(codename__in=[
        'add_brand',
        'modify_brand',
        'delete_brand',
        'change_node',
        'delete_node',
        'change_user',
        'change_conference',
        'mark_spam',
        'change_osfuser',
        'delete_osfuser',
        'change_preprintservice',
        'delete_preprintservice',
        'change_institution',
        'delete_institution',
        'change_institutionassetfile',
        'delete_institutionassetfile',
        'change_preprintprovider',
        'delete_preprintprovider',
        'change_subject',
        'change_maintenancestate',
        'change_registrationschema',
        'delete_maintenancestate',
        'change_scheduledbanner',
        'delete_scheduledbanner',
        'change_collectionprovider',
        'delete_collectionprovider',
        'change_providerassetfile',
        'delete_providerassetfile',
        'change_preprintrequest',
        'delete_preprintrequest',
        'change_registrationprovider',
        'delete_registrationprovider',
        'add_notabledomain',
        'change_notabledomain',
        'delete_notabledomain',
        'change_cedarmetadatatemplate',
    ])


def update_admin_permissions(verbosity=0):
    from django.contrib.auth.models import Group, Permission
    should_log = verbosity > 0
    # Create and add permissions for the read only group
    group, created = Group.objects.get_or_create(name='read_only')
    if created and should_log:
        logger.info('read_only group created')
    [group.permissions.add(perm) for perm in get_admin_read_permissions()]
    group.save()
    if should_log:
        logger.info('View permissions added to read only admin group')

    # Create  and add permissions for new OSF Admin group - can perform actions
    admin_group, created = Group.objects.get_or_create(name='osf_admin')
    if created and should_log:
        logger.info('admin_user Group created')
    [admin_group.permissions.add(perm) for perm in get_admin_read_permissions()]
    [admin_group.permissions.add(perm) for perm in get_admin_write_permissions()]
    group.save()
    if should_log:
        logger.info('Administrator permissions added to admin group')

    # Add a metrics_only Group and permissions
    metrics_group, created = Group.objects.get_or_create(name='metrics_only')
    if created and should_log:
        logger.info('Metrics only group created')
    metrics_permission = Permission.objects.get(codename='view_metrics')
    metrics_group.permissions.add(metrics_permission)
    metrics_group.save()


def update_provider_auth_groups(verbosity=0):
    # TODO: determine efficient way to only do this if perms change
    from osf.models.provider import AbstractProvider
    from django.db import transaction
    for subclass in AbstractProvider.__subclasses__():
        # The exception handling here allows us to make model changes to providers while also checking their permissions
        savepoint_id = transaction.savepoint()
        try:
            for obj in subclass.objects.all():
                obj.update_group_permissions()
                if verbosity > 0:
                    logger.info(f'Updated perms for {obj.type} {obj._id}')
        except ProgrammingError:
            logger.info('Schema change for AbstractProvider detected, passing.')
            transaction.savepoint_rollback(savepoint_id)


def update_permission_groups(sender, verbosity=0, **kwargs):
    if getattr(sender, 'label', None) == 'osf':
        update_admin_permissions(verbosity)
        update_provider_auth_groups(verbosity)


def update_license(sender, verbosity=0, **kwargs):
    if getattr(sender, 'label', None) == 'osf':
        from osf.utils.migrations import ensure_licenses
        ensure_licenses()


def update_waffle_flags(sender, verbosity=0, **kwargs):
    if getattr(sender, 'label', None) == 'osf':
        if 'pytest' not in sys.modules:
            manage_waffle()
            logger.info('Waffle flags have been synced')


def create_cache_table(sender, verbosity=0, **kwargs):
    if getattr(sender, 'label', None) == 'osf':
        call_command('createcachetable')


def update_default_providers(sender, verbosity=0, **kwargs):
    if getattr(sender, 'label', None) == 'osf':
        if 'pytest' in sys.modules:
            ensure_default_registration_provider()
        else:
            ensure_default_providers()


def ensure_default_providers():
    ensure_default_preprint_provider()
    ensure_default_registration_provider()


def ensure_default_preprint_provider():
    PreprintProvider = apps.get_model('osf', 'PreprintProvider')

    PreprintProvider.objects.update_or_create(
        _id=OSF_PREPRINTS_PROVIDER_DATA['_id'],
        defaults=OSF_PREPRINTS_PROVIDER_DATA
    )


def ensure_default_registration_provider():
    RegistrationProvider = apps.get_model('osf', 'RegistrationProvider')

    RegistrationProvider.objects.update_or_create(
        _id=OSF_REGISTRIES_PROVIDER_DATA['_id'],
        defaults=OSF_REGISTRIES_PROVIDER_DATA
    )


def add_registration_schemas(sender, verbosity=0, **kwargs):
    if getattr(sender, 'label', None) == 'osf':
        ensure_schemas()
        map_schemas_to_schemablocks()


def update_blocked_email_domains(sender, verbosity=0, **kwargs):
    if getattr(sender, 'label', None) == 'osf':
        from django.apps import apps
        NotableDomain = apps.get_model('osf', 'NotableDomain')
        for domain in osf_settings.BLACKLISTED_DOMAINS:
            NotableDomain.objects.update_or_create(
                domain=domain,
                defaults={'note': NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT},
            )


def update_storage_regions(sender, verbosity=0, **kwargs):
    if getattr(sender, 'label', None) == 'osf':
        ensure_default_storage_region()


def ensure_default_storage_region():
    osfstorage_config = apps.get_app_config('addons_osfstorage')
    Region = apps.get_model('addons_osfstorage', 'Region')
    Region.objects.get_or_create(
        _id=DEFAULT_REGION_ID,
        name=DEFAULT_REGION_NAME,
        defaults={
            'waterbutler_credentials': osfstorage_config.WATERBUTLER_CREDENTIALS,
            'waterbutler_settings': osfstorage_config.WATERBUTLER_SETTINGS,
            'waterbutler_url': osf_settings.WATERBUTLER_URL
        }
    )


def ensure_datacite_file_schema():
    """ Test use only """
    from osf.models import FileMetadataSchema
    with open('osf/metadata/schemas/datacite.json') as f:
        jsonschema = json.load(f)
    _, created = FileMetadataSchema.objects.get_or_create(
        _id='datacite',
        schema_version=1,
        defaults={
            'name': 'datacite',
            'schema': jsonschema
        }
    )


def ensure_invisible_and_inactive_schema():
    """ Test use only """
    from osf.models import RegistrationSchema
    v2_inactive_schema = [
        'EGAP Project',
        'OSF Preregistration',
        'Confirmatory - General',
        'RIDIE Registration - Study Complete',
        'RIDIE Registration - Study Initiation',
    ]
    v2_inactive_schema = v2_inactive_schema + ['Election Research Preacceptance Competition']
    RegistrationSchema.objects.filter(name__in=v2_inactive_schema).update(visible=False)
    RegistrationSchema.objects.filter(name__in=v2_inactive_schema).update(active=False)
