# -*- coding: utf-8 -*-
import sys
import logging
from dateutil.parser import parse
from scripts import utils as script_utils

import django
from django.db import transaction
django.setup()

from osf.models import Subject, PreprintProvider

logger = logging.getLogger(__name__)

CUSTOM_TAXONOMY_APPLIED_DATE = '2018-07-17T22:56:02.270217+00:00'
BP_TO_PSY_MAP = {
    'Animal Studies': 'Animal Learning and Behavior',
    'Anthropological Linguistics and Sociolinguistics': 'Anthropological Linguistics and Sociolinguistics',
    'Applied Linguistics': 'Applied Linguistics',
    'Behavioral Neurobiology': 'Behavioral Neuroscience',
    'Child Psychology': 'Developmental Psychology',
    'Clinical Psychology': 'Clinical Psychology',
    'Cognition and Perception': 'Perception',
    'Cognitive Neuroscience': 'Cognitive Neuroscience',
    'Cognitive Psychology': 'Cognitive Psychology',
    'Community Psychology': 'Community',
    'Comparative and Historical Linguistics': 'Historical Linguistics',
    'Computational Linguistics': 'Computational Linguistics',
    'Computational Neuroscience': 'Computational Neuroscience',
    'Counseling Psychology': 'Intervention Research',
    'Developmental Neuroscience': 'Developmental Neuroscience',
    'Developmental Psychology': 'Developmental Psychology',
    'Discourse and Text Linguistics': 'Text and Discourse',
    'Educational Psychology': 'Educational Psychology',
    'Engineering': 'Engineering Psychology',
    'Ergonomics': 'Ergonomics',
    'Evolution': 'Evolution',
    'First and Second Language Acquisition': 'First and Second Language Acquisition',
    'Health Psychology': 'Health Psychology',
    'Industrial and Organizational Psychology': 'Industrial and Organizational Psychology',
    'Language Description and Documentation': 'Language Description and Documentation',
    'Law and Psychology': 'Forensic and Legal Psychology',
    'Life Sciences': 'Life Sciences',
    'Linguistics': 'Linguistics',
    'Mental Disorders': 'Mental Disorders',
    'Molecular and Cellular Neuroscience': 'Molecular and Cellular Neuroscience',
    'Morphology': 'Morphology',
    'Multicultural Psychology': 'Multi-cultural Psychology',
    'Music': 'Music',
    'Neuroscience and Neurobiology': 'Neuroscience',
    'Other Environmental Sciences': 'Environmental Psychology',
    'Other Neuroscience and Neurobiology': 'Other Neuroscience and Neurobiology',
    'Personality and Social Contexts': 'Social and Personality Psychology',
    'Phonetics and Phonology': 'Phonetics and Phonology',
    'Physiology': 'Physiology',
    'Psychiatry': 'Psychiatry',
    'Psycholinguistics and Neurolinguistics': 'Psycholinguistics and Neurolinguistics',
    'Psychology': 'Psychology, other',
    'Quantitative Psychology': 'Quantitative Methods',
    'Research Methods in Life Sciences': 'Meta-science',
    'School Psychology': 'School Psychology',
    'Science and Technology Policy': 'Science and Technology Policy',
    'Semantics and Pragmatics': 'Semantics and Pragmatics',
    'Social Psychology': 'Social and Personality Psychology',
    'Social and Behavioral Sciences': 'Social and Behavioral Sciences',
    'Sports Studies': 'Sport Psychology',
    'Syntax': 'Syntax',
    'Systems Neuroscience': 'Systems Neuroscience',
    'Theory and Philosophy': 'Theory and Philosophy of Science',
    'Typological Linguistics and Linguistic Diversity': 'Typological Linguistics and Linguistic Diversity'
}


def main(dry_run=True):
    psy = PreprintProvider.load('psyarxiv')
    target_date = parse(CUSTOM_TAXONOMY_APPLIED_DATE)
    target_preprints = psy.preprint_services.filter(created__lte=target_date)

    i = 0
    for pp in target_preprints:
        i += 1
        original_modified = pp.modified
        logger.info('Preparing to migrate preprint {}'.format(pp._id))
        bps = Subject.objects.filter(id__in=pp.subjects.values_list('bepress_subject', flat=True))
        correct_subjects = Subject.objects.filter(provider=psy, text__in=[BP_TO_PSY_MAP[s.text] for s in bps])
        logger.info('Replacing subjects {} with {} on {}'.format(
            pp.subjects.values_list('text', flat=True),
            correct_subjects.values_list('text', flat=True),
            pp._id
        ))
        pp.subjects = correct_subjects
    logger.info('Successfully migrated {} preprints'.format(i))

    if dry_run:
        # When running in dry_run mode force the transaction to rollback
        raise Exception('Dry Run complete -- not committed')

if __name__ == '__main__':
    dry_run = '--dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    with transaction.atomic():
        main(dry_run=dry_run)
