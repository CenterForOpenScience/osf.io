# -*- coding: utf-8 -*-
<<<<<<< HEAD
import re
import os
import io
import sys
import zipfile
import requests

=======
import sys
>>>>>>> b2f6e94ac09df54df9e79ae8f529a068c88db8d1
import logging
from django.apps import apps
from django.db.utils import ProgrammingError
from osf.management.commands.manage_switch_flags import manage_waffle
from django.core.management import call_command
from api.base import settings


logger = logging.getLogger(__file__)
from django.db import transaction
from lxml import etree
from urllib.parse import urlparse

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



def ensure_citation_styles():
    CitationStyle = apps.get_model('osf', 'citationstyle')
    zip_data = io.BytesIO(requests.get('https://codeload.github.com/CenterForOpenScience/styles/zip/refs/heads/master').content)
    with transaction.atomic():
        with zipfile.ZipFile(zip_data) as zip_file:
            for file_name in [name for name in zip_file.namelist() if name.endswith('.zip') and not name.startswith('dependent')]:
                root = etree.fromstring(zip_file.read(file_name))

                namespace = re.search(r'\{.*\}', root.tag).group()
                title = root.find('{namespace}info/{namespace}title'.format(namespace=f'{namespace}')).text
                has_bibliography = 'Bluebook' in title

                if not has_bibliography:
                    bib = root.find(f'{{{namespace}}}bibliography')
                    layout = bib.find(f'{{{namespace}}}layout') if bib is not None else None
                    has_bibliography = True
                    if layout is not None and len(layout.getchildren()) == 1 and 'choose' in layout.getchildren()[0].tag:
                        choose = layout.find(f'{{{namespace}}}choose')
                        else_tag = choose.find(f'{{{namespace}}}else')
                        if else_tag is None:
                            supported_types = []
                            match_none = False
                            for child in choose.getchildren():
                                types = child.get('type', None)
                                match_none = child.get('match', 'any') == 'none'
                                if types is not None:
                                    types = types.split(' ')
                                    supported_types.extend(types)
                                    if 'webpage' in types:
                                        break
                            else:
                                if len(supported_types) and not match_none:
                                    # has_bibliography set to False now means that either bibliography tag is absent
                                    # or our type (webpage) is not supported by the current version of this style.
                                    has_bibliography = False

                summary = getattr(
                    root.find('{namespace}info/{namespace}summary'.format(namespace=f'{namespace}')), 'text', None
                )
                short_title = getattr(
                    root.find('{namespace}info/{namespace}title-short'.format(namespace=f'{namespace}')), 'text', None
                )
                # Required
                fields = {
                    '_id': os.path.splitext(os.path.basename(file_name))[0],
                    'title': title,
                    'has_bibliography': has_bibliography, 'parent_style': None,
                    'short_title': short_title,
                    'summary': summary
                }

                CitationStyle.objects.update_or_create(**fields)

            for file_name in [name for name in zip_file.namelist() if name.endswith('.zip') and name.startswith('dependent')]:
                root = etree.fromstring(zip_file.read(file_name))

                namespace = re.search(r'\{.*\}', root.tag).group()
                title = root.find('{namespace}info/{namespace}title'.format(namespace=f'{namespace}')).text
                has_bibliography = root.find(f'{{{namespace}}}bibliography') is not None or 'Bluebook' in title

                style_id = os.path.splitext(os.path.basename(file_name))[0]
                links = root.findall('{namespace}info/{namespace}link'.format(namespace=f'{namespace}'))
                for link in links:
                    if link.get('rel') == 'independent-parent':
                        parent_style_id = urlparse(link.get('href')).path.split('/')[-1]
                        parent_style = CitationStyle.objects.get(_id=parent_style_id)

                        if parent_style is not None:
                            summary = getattr(
                                root.find('{namespace}info/{namespace}summary'.format(namespace=f'{namespace}')),
                                'text', None
                            )
                            short_title = getattr(
                                root.find('{namespace}info/{namespace}title-short'.format(namespace=f'{namespace}')),
                                'text', None
                            )

                            parent_has_bibliography = parent_style.has_bibliography
                            fields = {
                                '_id': style_id,
                                'title': title,
                                'has_bibliography': parent_has_bibliography,
                                'parent_style': parent_style_id,
                                'short_title': short_title,
                                'summary': summary
                            }
                            CitationStyle.objects.update_or_create(**fields)
                            break
                        else:
                            logger.debug('Unable to load parent_style object: parent {}, dependent style {}'.format(parent_style_id, style_id))
                else:
                    fields = {
                        '_id': style_id,
                        'title': title,
                        'has_bibliography': has_bibliography,
                        'parent_style': None
                    }
                    CitationStyle.objects.update_or_create(**fields)


def update_citation_styles(sender, verbosity=0, **kwargs):
    if getattr(sender, 'label', None) == 'osf':
        if 'pytest' not in sys.modules:
            ensure_citation_styles()


def update_waffle_flags(sender, verbosity=0, **kwargs):
    if getattr(sender, 'label', None) == 'osf':
        if 'pytest' not in sys.modules:
            manage_waffle()
            logger.info('Waffle flags have been synced')


def create_cache_table(sender, verbosity=0, **kwargs):
    if getattr(sender, 'label', None) == 'osf':
        call_command('createcachetable', tablename=settings.CACHES[settings.STORAGE_USAGE_CACHE_NAME]['LOCATION'])
