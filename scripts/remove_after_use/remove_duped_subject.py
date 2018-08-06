# -*- coding: utf-8 -*-
import sys
import logging

from dateutil.parser import parse
from website.app import setup_django
setup_django()

from osf.models import PreprintService, Subject
from scripts import utils as script_utils

logger = logging.getLogger(__name__)

CUSTOM_TAXONOMY_APPLIED_DATE = '2018-07-17T22:56:02.270217+00:00'

def main(dry=True):
    date_of_interest = parse(CUSTOM_TAXONOMY_APPLIED_DATE)

    bad_subj = Subject.objects.get(text=' Social and Personality Psychology', provider___id='psyarxiv')
    good_subj = Subject.objects.get(text='Social and Personality Psychology', provider___id='psyarxiv')

    existing_preprints_with_bad_subj = PreprintService.objects.filter(created__lte=date_of_interest, subjects__in=[bad_subj])
    new_preprints_with_bad_subj = PreprintService.objects.filter(created__gt=date_of_interest, subjects__in=[bad_subj])

    num_existing = existing_preprints_with_bad_subj.count()
    for preprint in existing_preprints_with_bad_subj:
        assert preprint.subjects.exclude(id=bad_subj.id).filter(bepress_subject=bad_subj.bepress_subject).exists()
        preprint.subjects.remove(bad_subj)
        logger.info('Removed subject "{}" from preprint {}'.format(bad_subj.text, preprint._id))

    logger.info('Subject "{}" removed from {} preprints'.format(bad_subj.text, num_existing))

    num_new = new_preprints_with_bad_subj.count()
    for preprint in new_preprints_with_bad_subj:
        preprint.subjects.remove(bad_subj)
        preprint.subjects.add(good_subj)
        logger.info('Replaced subject "{}" with subject "{}" on preprint {}'.format(bad_subj.text, good_subj.text, preprint._id))

    logger.info('Subject "{}" replaced with "{}" on {} preprints'.format(bad_subj.text, good_subj.text, num_new))
    logger.info('Deleting subject "{}" with id {}'.format(bad_subj.text, bad_subj.id))

    bad_subj.delete()

    logger.info('Done.')

if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
