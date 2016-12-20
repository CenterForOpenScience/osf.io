import os
import json
import logging
import sys

from modularodm import Q, storage
from modularodm.exceptions import NoResultsFound

from framework.mongo import set_up_storage
from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils
from website import settings
from website.project.taxonomies import Subject


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def update_taxonomies(filename):
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

            try:
                subject = Subject.find_one(Q('text', 'eq', text))
                logger.info('Found existing Subject "{}":{}{}'.format(
                    subject.text,
                    subject._id,
                    u' with parent {}:{}'.format(parent.text, parent._id) if parent else ''
                ))
            except (NoResultsFound):
                # If subject does not yet exist, create it
                subject = Subject(
                    text=text,
                    parents=[parent] if parent else [],
                )
                logger.info(u'Creating Subject "{}":{}{}'.format(
                    subject.text,
                    subject._id,
                    u' with parent {}:{}'.format(parent.text, parent._id) if parent else ''
                ))
            else:
                # If subject does exist, append parent_id if not already added
                if parent and parent not in subject.parents:
                    subject.parents.append(parent)
                    logger.info(u'Adding parent "{}":{} to Subject "{}":{}'.format(
                        parent.text, parent._id,
                        subject.text, subject._id
                    ))

            subject.save()

def main():
    dry_run = '--dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    set_up_storage([Subject], storage.MongoStorage)
    with TokuTransaction():
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
