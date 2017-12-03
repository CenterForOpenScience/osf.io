# -*- coding: utf-8 -*-

'''
A management command to populate preprint providers for local development.

The preprint providers populated in this script do not accurately reflect
the preprint providers that appear on staging or production environments,
and are for testing/local development purposes only.

In order to make additional changes to a preprint provider
(i.e. set description, advisory_board, external_url, etc.),
you should run the admin app which will allow you to edit a preprint provider.

Before running this command, you should run the update_taxonomies script
to populate subjects (if you haven't already). The update_taxonomies script
will create the OSF preprint provider.
'''

from __future__ import unicode_literals
import json
import logging


import django
django.setup()

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from osf.models import NodeLicense, Subject, PreprintProvider
from scripts import utils as script_utils
from website.settings import PREPRINT_PROVIDER_DOMAINS

logger = logging.getLogger(__name__)


def format_domain_url(domain):
    return ''.join((PREPRINT_PROVIDER_DOMAINS['prefix'], str(domain), PREPRINT_PROVIDER_DOMAINS['suffix'])) if \
        PREPRINT_PROVIDER_DOMAINS['enabled'] else ''


SUBJECTS_CACHE = {}
PREPRINT_PROVIDERS = [
    {
        '_id': 'lawarxiv',
        'name': '[TEST] LawArXiv',
        'share_publish_type': 'Preprint',
        'share_title': 'LawArXiv',
        'default_license': 'CC0 1.0 Universal',
        'licenses_acceptable': ['CC0 1.0 Universal', 'No license'],
        'description': 'Straight bepress taxonomy, no custom domain, two licenses',
    },
    {
        '_id': 'socarxiv',
        'name': '[TEST] SocArXiv',
        'share_publish_type': 'Preprint',
        'share_title': 'SocArXiv',
        'domain': format_domain_url('socarxiv.org'),
        'domain_redirect_enabled': True,
        'default_license': 'CC0 1.0 Universal',
        'licenses_acceptable': ['CC0 1.0 Universal'],
        'description': 'Straight except custom domain that redirects to that domain, one license',
    },
    {
        '_id': 'psyarxiv',
        'name': '[TEST] PsyArXiv',
        'share_publish_type': 'Preprint',
        'share_title': 'PsyArXiv',
        'domain': format_domain_url('psyarxiv.com'),
        'domain_redirect_enabled': False,
        'default_license': 'No license',
        'licenses_acceptable': ['CC0 1.0 Universal', 'CC-By Attribution 4.0 International', 'No license'],
        'subjects_acceptable': [
            (['Life Sciences', 'Neuroscience and Neurobiology', 'Cognitive Neuroscience'], False),
            (['Social and Behavioral Sciences', 'Psychology'], True),
        ],
        'description': 'Basic change to taxonomy showing some simple hierarchy, a custom domain but no redirect, three licenses',
    },
    {
        '_id': 'engrxiv',
        'name': '[TEST] engrXiv',
        'share_publish_type': 'Preprint',
        'share_title': 'EngrXiv',
        'external_url': 'http://engrxiv.com',
        'default_license': 'CC0 1.0 Universal',
        'licenses_acceptable': ['CC0 1.0 Universal', 'CC-By Attribution 4.0 International', 'No license'],
        'description': 'Custom taxonomy, no custom domain, all the licenses',
        'custom_taxonomy': {
            'include': ['Engineering'],
            'exclude': ['Manufacturing', 'Heat Transfer, Combustion', 'Aerodynamics and Fluid Mechanics'],
            'custom': {
                'Architectural Engineering': {
                    'parent': 'Engineering',
                    'bepress': 'Architectural Engineering'
                }
            },
            'merge': {
                'Architecture': 'Architectural Engineering'
            }
        }
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

def populate_preprint_providers(*args):
    for data in PREPRINT_PROVIDERS:
        _id = data.pop('_id')
        default_license = data.pop('default_license', False)
        licenses = [get_license(name) for name in data.pop('licenses_acceptable', [])]
        custom_taxonomy = data.pop('custom_taxonomy', False)

        if data.get('subjects_acceptable'):
            data['subjects_acceptable'] = map(
                lambda rule: (map(get_subject_id, rule[0]), rule[1]),
                data['subjects_acceptable']
            )

        provider, created = PreprintProvider.objects.update_or_create(_id=_id, defaults=data)

        if licenses:
            provider.licenses_acceptable.add(*licenses)
        if default_license:
            provider.default_license = get_license(default_license)
        if custom_taxonomy:
            logger.info('Adding custom taxonomy for: {}'.format(_id))
            call_command('populate_custom_taxonomies', '--provider', _id, '--data', json.dumps(custom_taxonomy))
        if created:
            logger.info('Added preprint provider: {}'.format(_id))
        else:
            logger.info('Updated preprint provider: {}'.format(_id))

def remove_preprint_providers(*args):
    providers = PreprintProvider.objects.exclude(_id='osf')
    for provider in providers:
        logger.info('Removing preprint provider: {}'.format(provider._id))
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
            help='Removes preprint providers'
        )

    def handle(self, *args, **options):
        reverse = options.get('reverse', False)
        dry_run = options.get('dry_run', False)
        if not dry_run:
            script_utils.add_file_logger(logger, __file__)
        with transaction.atomic():
            if reverse:
                remove_preprint_providers()
            else:
                populate_preprint_providers()
            if dry_run:
                raise RuntimeError('Dry run, transaction rolled back.')
