# -*- coding: utf-8 -*-

'''
A management command to populate collection providers for local development.

The collection providers populated in this script do not accurately reflect
the collection providers that appear on staging or production environments,
and are for testing/local development purposes only.

In order to make additional changes to a collection provider
(i.e. set description, advisory_board, external_url, etc.),
you should run the admin app which will allow you to edit a collection provider.

Before running this command, you should run the update_taxonomies script
to populate subjects (if you haven't already). The update_taxonomies script
will create the OSF collection provider.
'''

from __future__ import unicode_literals
import json
import logging


import django
django.setup()

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from osf.models import NodeLicense, Subject, CollectionProvider, AbstractProvider
from scripts import utils as script_utils
from website.settings import PREPRINT_PROVIDER_DOMAINS
import random

from osf_tests import factories

logger = logging.getLogger(__name__)


def format_domain_url(domain):
    return ''.join((PREPRINT_PROVIDER_DOMAINS['prefix'], str(domain), PREPRINT_PROVIDER_DOMAINS['suffix'])) if \
        PREPRINT_PROVIDER_DOMAINS['enabled'] else ''


SUBJECTS_CACHE = {}
PROVIDERS = [
    {
        '_id': 'studyswap',
        'name': '[TEST] StudySwap',
        'default_license': 'CC0 1.0 Universal',
        'licenses_acceptable': ['CC0 1.0 Universal', 'No license'],
        'description': 'Straight bepress taxonomy, no custom domain, two licenses',
        'primary_collection': {
            'is_public': True,
            'is_promoted': True,
            'is_bookmark_collection': False,
            'title': 'StudySwap\'s Primary Collection',
            'collected_type_choices': [
                'Have Participants',
                'Need Participants',
            ],
            'status_choices': [
                'Open',
                'Complete',
            ],
        },
    },
    {
        '_id': 'flubber',
        'name': '[TEST] Absent-minded Professor Collection',
        'domain': format_domain_url('flubber.org'),
        'domain_redirect_enabled': True,
        'default_license': 'CC0 1.0 Universal',
        'licenses_acceptable': ['CC0 1.0 Universal'],
        'description': 'Straight except custom domain that redirects to that domain, one license',
        'primary_collection': {
            'is_public': True,
            'is_promoted': True,
            'is_bookmark_collection': False,
            'title': 'Very bouncey things',
            'collected_type_choices': [
                'Forgotten',
                'Remebered',
            ],
            'status_choices': [
                'In-progess',
                'Almost done',
                'Complete',
            ],
        },
    },
    {
        '_id': 'apa',
        'name': '[TEST] American Psychological Association',
        'domain': format_domain_url('collections.apa.org'),
        'domain_redirect_enabled': False,
        'default_license': 'No license',
        'licenses_acceptable': ['CC0 1.0 Universal', 'CC-By Attribution 4.0 International', 'No license'],
        'description': 'Basic change to taxonomy showing some simple hierarchy, a custom domain but no redirect, three licenses',
        'custom_taxonomy': {
            'include': ['Psychology'],
        },
        'primary_collection': {
            'is_public': True,
            'is_promoted': True,
            'is_bookmark_collection': False,
            'title': 'Future predections',
            'collected_type_choices': [
                'project',
                'paper',
            ],
            'status_choices': [
                'Debunked',
                'Confirmed',
            ],
        },
    },
]

def get_subject_id(name):
    if name not in SUBJECTS_CACHE:
        try:
            SUBJECTS_CACHE[name] = Subject.objects.filter(text=name).values_list('_id', flat=True).get()
        except Subject.DoesNotExist:
            raise Exception('Subject: "{}" not found'.format(name))

    return SUBJECTS_CACHE[name]

def get_license(name):
    try:
        license = NodeLicense.objects.get(name=name)
    except NodeLicense.DoesNotExist:
        raise Exception('License: "{}" not found'.format(name))
    return license

def populate_providers(add_data):
    for data in PROVIDERS:
        _id = data.pop('_id')
        default_license = data.pop('default_license', False)
        licenses = [get_license(name) for name in data.pop('licenses_acceptable', [])]
        custom_taxonomy = data.pop('custom_taxonomy', False)

        primary_collection = data.pop('primary_collection', False)

        provider, created = CollectionProvider.objects.update_or_create(_id=_id, defaults=data)

        if licenses:
            provider.licenses_acceptable.add(*licenses)

        if default_license:
            provider.default_license = get_license(default_license)

        if custom_taxonomy:
            logger.info('Adding custom taxonomy for: {}'.format(_id))
            call_command('populate_custom_taxonomies', '--provider', _id, '--data', json.dumps(custom_taxonomy))

        provider_subjects = provider.subjects.all()
        subjects = provider_subjects if len(provider_subjects) else AbstractProvider.objects.get(_id='osf').subjects.all()

        if primary_collection and not provider.primary_collection:
            primary_collection['provider'] = provider
            provider.primary_collection = factories.CollectionFactory(**primary_collection)
            provider.primary_collection.save()
            provider.save()

        if add_data and provider.primary_collection:
            user = factories.AuthUserFactory()
            user.save()

            for _ in range(5):
                node = factories.NodeFactory()
                node.is_public = True
                node.save()

                status = random.choice(provider.primary_collection.status_choices)
                collected_type = random.choice(provider.primary_collection.collected_type_choices)
                cgm = provider.primary_collection.collect_object(node, user, collected_type=collected_type, status=status)
                rando_subjects = random.sample(subjects, min(len(subjects), 5))
                cgm.subjects.add(*rando_subjects)
                cgm.save()

        logger.info('{} collection provider: {}'.format('Added' if created else 'Updated', _id))

def remove_providers(*args):
    providers = CollectionProvider.objects.exclude(_id='osf')
    for provider in providers:
        logger.info('Removing collection provider: {}'.format(provider._id))
        provider.delete()


class Command(BaseCommand):

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Run migration and roll back changes to db',
        )
        parser.add_argument(
            '--reverse',
            action='store_true',
            dest='reverse',
            help='Removes collection providers'
        )
        parser.add_argument(
            '--add-data',
            action='store_true',
            dest='add_data',
            help='Adds data to the primary collection'
        )

    def handle(self, *args, **options):
        reverse = options.get('reverse', False)
        dry_run = options.get('dry_run', False)
        add_data = options.get('add_data', False)

        if not dry_run:
            script_utils.add_file_logger(logger, __file__)

        with transaction.atomic():
            if reverse:
                remove_providers()
            else:
                populate_providers(add_data)

            if dry_run:
                raise RuntimeError('Dry run, transaction rolled back.')
