# -*- coding: utf-8 -*-
import logging

from django.db.models import Q

logger = logging.getLogger(__file__)


# Admin group permissions
def get_admin_read_permissions():
    from django.contrib.auth.models import Permission
    return Permission.objects.filter(codename__in=[
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
    ])


def get_admin_write_permissions():
    from django.contrib.auth.models import Permission
    return Permission.objects.filter(codename__in=[
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


def get_admin_prereg_permissions():
    from django.contrib.auth.models import Permission
    return Permission.objects.filter(codename__in=[
        'view_prereg',
        'administer_prereg',
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

    # Create and add permissions for Prereg Admin group
    prereg_group, created = Group.objects.get_or_create(name='prereg_admin')
    if created and should_log:
        logger.info('Prereg admin group created')
    [prereg_group.permissions.add(perm) for perm in get_admin_prereg_permissions()]
    prereg_group.save()
    if should_log:
        logger.info('Prereg read and administer permissions added to the prereg_admin group')

    # Add a metrics_only Group and permissions
    metrics_group, created = Group.objects.get_or_create(name='metrics_only')
    if created and should_log:
        logger.info('Metrics only group created')
    metrics_permission = Permission.objects.get(codename='view_metrics')
    metrics_group.permissions.add(metrics_permission)
    metrics_group.save()

    # Add a view_prereg Group and permissions
    prereg_view_group, created = Group.objects.get_or_create(name='prereg_view')
    if created and should_log:
        logger.info('Prereg view group created')
    prereg_view_permission = Permission.objects.get(codename='view_prereg')
    prereg_view_group.permissions.add(prereg_view_permission)
    prereg_view_group.save()


def update_provider_auth_groups(verbosity=0):
    # TODO: determine efficient way to only do this if perms change
    from osf.models.provider import AbstractProvider
    for subclass in AbstractProvider.__subclasses__():
        for obj in subclass.objects.all():
            obj.update_group_permissions()
            if verbosity > 0:
                logger.info('Updated perms for {} {}'.format(obj.type, obj._id))

def update_permission_groups(sender, verbosity=0, **kwargs):
    if getattr(sender, 'label', None) == 'osf':
        update_admin_permissions(verbosity)
        update_provider_auth_groups(verbosity)
