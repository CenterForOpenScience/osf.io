from __future__ import unicode_literals

from django.db.models import Q
from django.db import migrations
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.core.management.sql import emit_post_migrate_signal

import logging

logger = logging.getLogger(__file__)


def get_read_only_permissions():
    return Permission.objects.filter(
        Q(codename='view_node') |
        Q(codename='view_registration') |
        Q(codename='view_user') |
        Q(codename='view_conference') |
        Q(codename='view_spam') |
        Q(codename='view_metrics') |
        Q(codename='view_desk')
    )


def get_admin_permissions():
    return Permission.objects.filter(
        Q(codename='change_node') |
        Q(codename='delete_node') |
        Q(codename='change_user') |
        Q(codename='change_conference') |
        Q(codename='mark_spam')
    )


def get_prereg_admin_permissions():
    return Permission.objects.filter(
        Q(codename='view_prereg') |
        Q(codename='administer_prereg')
    )


def add_group_permissions(*args):
    # this is to make sure that the permissions created in an earlier migration exist!
    emit_post_migrate_signal(2, False, 'default')

    # Create and add permissions for the read only group
    group, created = Group.objects.get_or_create(name='read_only')
    if created:
        logger.info('read_only group created')
    [group.permissions.add(perm) for perm in get_read_only_permissions()]
    group.save()
    logger.info('Node, user, spam and meeting permissions added to read only group')

    # Create  and add permissions for new OSF Admin group - can perform actions
    admin_group, created = Group.objects.get_or_create(name='osf_admin')
    if created:
        logger.info('admin_user Group created')
    [admin_group.permissions.add(perm) for perm in get_read_only_permissions()]
    [admin_group.permissions.add(perm) for perm in get_admin_permissions()]
    group.save()
    logger.info('Administrator permissions for Node, user, spam and meeting permissions added to admin group')

    # Create and add permissions for Prereg Admin group
    prereg_group, created = Group.objects.get_or_create(name='prereg_admin')
    if created:
        logger.info('Prereg admin group created')
    [prereg_group.permissions.add(perm) for perm in get_prereg_admin_permissions()]
    prereg_group.save()
    logger.info('Prereg read and administer permissions added to the prereg_admin group')

    # Add a metrics_only Group and permissions
    metrics_group, created = Group.objects.get_or_create(name='metrics_only')
    if created:
        logger.info('Metrics only group created')
    metrics_permission = Permission.objects.get(codename='view_metrics')
    metrics_group.permissions.add(metrics_permission)
    metrics_group.save()

    # Add a view_prereg Group and permissions
    prereg_view_group, created = Group.objects.get_or_create(name='prereg_view')
    if created:
        logger.info('Prereg view group created')
    prereg_view_permission = Permission.objects.get(codename='view_prereg')
    prereg_view_group.permissions.add(prereg_view_permission)
    prereg_view_group.save()


def remove_group_permissions(*args):
    # remove the read only group
    Group.objects.get(name='read_only').delete()

    # remove the prereg admin group
    Group.objects.get(name='prereg_admin').delete()

    # remove the osf admin group
    Group.objects.get(name='osf_admin').delete()

    # remove the  metrics group
    Group.objects.get(name='metrics_only').delete()

    # remove the new prereg view group
    Group.objects.get(name='prereg_view').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0007_alter_validators_add_error_messages'),
        ('osf', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_group_permissions, remove_group_permissions),
    ]
