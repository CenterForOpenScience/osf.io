import os
import json
import logging
import sys

from django.db import transaction
from django.apps import apps

from scripts import utils as script_utils
from scripts.populate_preprint_providers import update_or_create
from website.app import init_app
from website import settings


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Stolen from scripts.populate_preprint_providers for initial subject creation
OSF_PROVIDER_DATA = {
    '_id': 'osf',
    'name': 'Open Science Framework',
    'logo_name': 'cos-logo.png',
    'description': 'A scholarly commons to connect the entire research cycle',
    'banner_name': 'cos-banner.png',
    'domain': settings.DOMAIN,
    'domain_redirect_enabled': False,  # Never change this
    'external_url': 'https://osf.io/preprints/',
    'example': 'khbvy',
    'advisory_board': '',
    'email_contact': '',
    'email_support': '',
    'social_twitter': '',
    'social_facebook': '',
    'social_instagram': '',
    'licenses_acceptable': ['CC0 1.0 Universal', 'CC-By Attribution 4.0 International', 'No license'],
    'header_text': '',
    'subjects_acceptable': [],
}

def update_taxonomies(filename):
    Subject = apps.get_model('osf.Subject')
    PreprintProvider = apps.get_model('osf.PreprintProvider')
    try:
        bepress_provider = PreprintProvider.objects.get(_id='osf')
    except PreprintProvider.DoesNotExist:
        bepress_provider, _ = update_or_create(OSF_PROVIDER_DATA)
    # Flat taxonomy is stored locally, read in here
    with open(
        os.path.join(
            settings.APP_PATH,
            'website', 'static', filename
        )
    ) as fp:
        taxonomy = json.load(fp)

        for subject_path in taxonomy.get('data'):
            subjects = subject_path.split('_')
            text = subjects[-1]

            # Search for parent subject, get id if it exists
            parent = None
            if len(subjects) > 1:
                parent, created_p = Subject.objects.get_or_create(text=subjects[-2], provider=bepress_provider)
                if created_p:
                    logger.info('Created parent "{}":{} for subject {}'.format(parent.text, parent._id, text))
            logger.info(u'Getting or creating Subject "{}"{}'.format(
                text,
                u' with parent {}:{}'.format(parent.text, parent._id) if parent else ''
            ))
            subject, _ = Subject.objects.get_or_create(text=text, provider=bepress_provider)
            if parent and not subject.parent:
                logger.info(u'Adding parent "{}":{} to Subject "{}":{}'.format(
                    parent.text, parent._id,
                    subject.text, subject._id
                ))
                subject.parent = parent
                subject.save()

def main():
    init_app(set_backends=True, routes=False)
    dry_run = '--dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    with transaction.atomic():
        update_taxonomies('bepress_taxonomy.json')
        if dry_run:
            raise RuntimeError('Dry run, transaction rolled back')

if __name__ == '__main__':
    main()
