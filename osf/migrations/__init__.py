# -*- coding: utf-8 -*-
import json
from django.apps import apps
import sys
import logging

from django.db.utils import ProgrammingError
from django.core.management import call_command

from api.base import settings as api_settings
from osf.management.commands.manage_switch_flags import manage_waffle
from osf.utils.migrations import ensure_schemas, map_schemas_to_schemablocks
from website import settings as osf_settings

logger = logging.getLogger(__file__)


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
        'view_preprintprovider',
        'view_subject',
        'view_scheduledbanner',
        'view_collectionprovider',
        'view_providerassetfile',
        'view_registrationprovider',
        'view_management',
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
                    logger.info('Updated perms for {} {}'.format(obj.type, obj._id))
        except ProgrammingError:
            logger.info('Schema change for AbstractProvider detected, passing.')
            transaction.savepoint_rollback(savepoint_id)


def update_permission_groups(sender, verbosity=0, **kwargs):
    if getattr(sender, 'label', None) == 'osf':
        update_admin_permissions(verbosity)
        update_provider_auth_groups(verbosity)


def ensure_subjects():
    Subject = apps.get_model('osf.subject')
    PreprintProvider = apps.get_model('osf.preprintprovider')
    bepress_provider, _ = PreprintProvider.objects.get_or_create(
        _id='osf',
    )
    # Flat taxonomy is stored locally, read in here
    with open(osf_settings.SUBJECT_PATH) as fp:
        taxonomy = json.load(fp)

        for subject_path in taxonomy.get('data'):
            subjects = subject_path.split('_')
            text = subjects[-1]

            # Search for parent subject, get id if it exists
            parent = None
            if len(subjects) > 1:
                parent, _ = Subject.objects.update_or_create(
                    text=subjects[-2],
                    defaults={'provider': bepress_provider}
                )
            subject, _ = Subject.objects.update_or_create(
                text=text,
                defaults={'provider': bepress_provider}
            )
            if parent and not subject.parent:
                subject.parent = parent
                subject.save()


def update_subjects(sender, verbosity=0, **kwargs):
    if getattr(sender, 'label', None) == 'osf':
        ensure_subjects()


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
        call_command('createcachetable', tablename=api_settings.CACHES[api_settings.STORAGE_USAGE_CACHE_NAME]['LOCATION'])


def add_registration_schemas(sender, verbosity=0, **kwargs):
    if getattr(sender, 'label', None) == 'osf':
        ensure_schemas()
        map_schemas_to_schemablocks()


def update_blocked_email_domains(sender, verbosity=0, **kwargs):
    if getattr(sender, 'label', None) == 'osf':
        from django.apps import apps
        NotableEmailDomain = apps.get_model('osf', 'NotableEmailDomain')
        for domain in osf_settings.BLACKLISTED_DOMAINS:
            NotableEmailDomain.objects.update_or_create(
                domain=domain,
                defaults={'note': NotableEmailDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION},
            )
