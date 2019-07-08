# -*- coding: utf-8 -*-
# TODO: squashmigrations, replace this with initial_data
from __future__ import unicode_literals
import json
import logging
import os

from django.conf import settings
from django.db import migrations
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from website.settings import DOMAIN, APP_PATH

OSF_PREPRINTS_DATA = {
    '_id': 'osf',
    'type': 'osf.preprintprovider',
    'name': 'Open Science Framework',
    'domain': DOMAIN,
    'domain_redirect_enabled': False,
    'default_license': 'CC0 1.0 Universal',
    'licenses_acceptable': ['CC0 1.0 Universal', 'CC-By Attribution 4.0 International', 'No license'],
}
OSF_REGISTRIES_DATA = {
    '_id': 'osf',
    'type': 'osf.registrationprovider',
    'name': 'OSF Registries',
    'domain': DOMAIN,
    'domain_redirect_enabled': False,
    'default_license': 'CC0 1.0 Universal',
    'licenses_acceptable': ['CC0 1.0 Universal', 'CC-By Attribution 4.0 International', 'No license'],
}

def _create_provider(cls, data, state):
    NodeLicense = state.get_model('osf.nodelicense')

    def get_license(name):
        try:
            license = NodeLicense.objects.get(name=name)
        except NodeLicense.DoesNotExist:
            raise Exception('License: "{}" not found'.format(name))
        return license

    licenses = [get_license(name) for name in data.pop('licenses_acceptable', [])]
    default_license = data.pop('default_license', False)
    provider = cls.objects.create(**data)
    if licenses:
        provider.licenses_acceptable.add(*licenses)
    if default_license:
        provider.default_license = get_license(default_license)
    provider.save()

def create_osf_preprints(state, schema):
    AbstractProvider = state.get_model('osf.abstractprovider')
    if not AbstractProvider.objects.filter(_id=OSF_PREPRINTS_DATA['_id'], type=OSF_PREPRINTS_DATA['type']).exists():
        logger.info('Creating PreprintProvider "osf"')
        _create_provider(AbstractProvider, OSF_PREPRINTS_DATA, state)

def create_subjects(state, schema):
    Subject = state.get_model('osf.subject')
    AbstractProvider = state.get_model('osf.abstractprovider')
    if not Subject.objects.exists():
        logger.info('Populating Subjects')
        bepress_provider = AbstractProvider.objects.get(type=OSF_PREPRINTS_DATA['type'], _id=OSF_PREPRINTS_DATA['_id'])
        # Flat taxonomy is stored locally, read in here
        with open(
            os.path.join(
                APP_PATH,
                'website', 'static', 'bepress_taxonomy.json',
            )
        ) as fp:
            taxonomy = json.load(fp)

            for subject_path in taxonomy.get('data'):
                subjects = subject_path.split('_')
                text = subjects[-1]

                # Search for parent subject, get id if it exists
                parent = None
                if len(subjects) > 1:
                    parent, _ = Subject.objects.get_or_create(text=subjects[-2], provider=bepress_provider)
                subject, _ = Subject.objects.get_or_create(text=text, provider=bepress_provider)
                if parent and not subject.parent:
                    subject.parent = parent
                    subject.save()

def create_osf_registries(state, schema):
    AbstractProvider = state.get_model('osf.abstractprovider')
    if not AbstractProvider.objects.filter(_id=OSF_REGISTRIES_DATA['_id'], type=OSF_REGISTRIES_DATA['type']).exists():
        logger.info('Creating RegistrationProvider "osf"')
        _create_provider(AbstractProvider, OSF_REGISTRIES_DATA, state)

def noop(*args, **kwargs):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0137_auto_20181012_1756'),
    ]

    operations = [] if getattr(settings, 'TEST_ENV', False) else [
        migrations.RunPython(create_osf_preprints, noop),
        migrations.RunPython(create_subjects, noop),
        migrations.RunPython(create_osf_registries, noop),
    ]
