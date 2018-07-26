from __future__ import unicode_literals
import logging

from django.core.management.sql import emit_post_migrate_signal
from django.db import migrations
from django.db.models import Q
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission

logger = logging.getLogger(__file__)


def get_new_read_only_permissions():
    return Permission.objects.filter(
        Q(codename='view_collectionprovider')
    )


def get_new_admin_permissions():
    return Permission.objects.filter(
        Q(codename='change_collectionprovider') |
        Q(codename='delete_collectionprovider')
    )


def add_group_permissions(*args):
    # this is to make sure that the permissions created in an earlier migration exist!
    emit_post_migrate_signal(2, False, 'default')

    # Add permissions for the read only group
    read_only_group = Group.objects.get(name='read_only')
    [read_only_group.permissions.add(perm) for perm in get_new_read_only_permissions()]
    read_only_group.save()
    logger.info('Collection Provider permissions added to read only group')

    # Add permissions for new OSF Admin group - can perform actions
    admin_group = Group.objects.get(name='osf_admin')
    [admin_group.permissions.add(perm) for perm in get_new_read_only_permissions()]
    [admin_group.permissions.add(perm) for perm in get_new_admin_permissions()]
    admin_group.save()
    logger.info('Administrator permissions for Collection Providers added to admin group')


def remove_group_permissions(*args):
    # remove the read only group
    read_only_group = Group.objects.get(name='read_only')
    [read_only_group.permissions.remove(perm) for perm in get_new_read_only_permissions()]
    read_only_group.save()

    # remove the osf admin group
    admin_group = Group.objects.get(name='osf_admin')
    [admin_group.permissions.remove(perm) for perm in get_new_read_only_permissions()]
    [admin_group.permissions.remove(perm) for perm in get_new_admin_permissions()]
    admin_group.save()


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0112_alter_collectionprovider_permissions'),
    ]

    operations = [
        migrations.RunPython(add_group_permissions, remove_group_permissions),
    ]
