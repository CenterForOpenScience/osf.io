import os
import json
import logging
import sys

from django.db import transaction
from django.apps import apps
from modularodm import Q, storage
from modularodm.exceptions import NoResultsFound

from framework.mongo import set_up_storage
from scripts import utils as script_utils
from website.app import init_app
from website import settings


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def update_taxonomies(filename):
    Subject = apps.get_model('osf.Subject')
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
                try:
                    parent = Subject.find_one(Q('text', 'eq', subjects[-2]))
                except NoResultsFound:
                    pass
            parents = [parent] if parent else []
            try:
                subject = Subject.find_one(Q('text', 'eq', text))
                logger.info('Found existing Subject "{}":{}{}'.format(
                    subject.text,
                    subject._id,
                    u' with parent {}:{}'.format(parent.text, parent._id) if parent else ''
                ))
            except (NoResultsFound):
                # If subject does not yet exist, create it
                subject = Subject(text=text)
                subject.save()
                logger.info(u'Creating Subject "{}":{}{}'.format(
                    subject.text,
                    subject._id,
                    u' with parent {}:{}'.format(parent.text, parent._id) if parent else ''
                ))
            if parent and not subject.parents.filter(id=parent.id).exists():
                logger.info(u'Adding parent "{}":{} to Subject "{}":{}'.format(
                    parent.text, parent._id,
                    subject.text, subject._id
                ))
                subject.parents.add(parent)
            subject.save()

def main():
    init_app(set_backends=True, routes=False)
    Subject = apps.get_model('osf.Subject')
    dry_run = '--dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    with transaction.atomic():
        update_taxonomies('bepress_taxonomy.json')
        # Now that all subjects have been added to the db, compute and set
        # the 'children' field for every subject
        logger.info('Setting "children" field for each Subject')
        for subject in Subject.find():
            subject.children = Subject.find(Q('parents', 'eq', subject))
            subject.save()
        if dry_run:
            raise RuntimeError('Dry run, transaction rolled back')

if __name__ == '__main__':
    main()
