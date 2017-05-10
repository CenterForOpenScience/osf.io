import json
import logging

import django
django.setup()
from django.core.management.base import BaseCommand
from django.db import transaction

from osf.models import PreprintProvider, PreprintService, Subject
from scripts import utils as script_utils
from website.project.taxonomies import validate_subject_hierarchy

logger = logging.getLogger(__name__)

BEPRESS_PROVIDER = PreprintProvider.objects.filter(_id='osf').first()

def validate_input(custom_provider, data):
    logger.info('Validating data')
    assert data.get('include'), 'Must specify Subjects to recursively include with `include`.'
    includes = data.get('include')
    excludes = data.get('exclude', [])
    customs = data.get('custom', {})
    for text in includes:
        assert Subject.objects.filter(provider=BEPRESS_PROVIDER, text=text).exists(), 'Unable to find included subject with text {}'.format(text)
    included_subjects = Subject.objects.filter(provider=BEPRESS_PROVIDER, text__in=includes).include_children()
    logger.info('Successfully validated `include`')
    for text in excludes:
        excluded = Subject.objects.get(provider=BEPRESS_PROVIDER, text=text)  # May raise not found error
        assert excluded.object_hierarchy[0].text in includes, 'Excluded subject with text {} was not included'.format(text)
    included_subjects.exclude(text__in=excludes)
    logger.info('Successfully validated `exclude`')
    for cust_name, map_dict in customs.iteritems():
        assert not included_subjects.filter(text=cust_name).exists(), 'Custom text {} already exists in mapped set'.format(cust_name)
        assert Subject.objects.filter(provider=BEPRESS_PROVIDER, text=map_dict.get('bepress')).exists(), 'Unable to find specified BePress subject with text {}'.format(map_dict.get('bepress'))
        if map_dict.get('parent'):  # Null parent possible
            assert map_dict['parent'] in set(customs.keys()) | set(included_subjects.values_list('text', flat=True)), 'Unable to find specified parent with text {} in mapped set'.format(map_dict['parent'])
            # TODO: hierarchy length validation? Probably more trouble than worth here, done on .save
    logger.info('Successfully validated `custom`')
    included_subjects = included_subjects | Subject.objects.filter(text__in=[map_dict['bepress'] for map_dict in customs.values()])
    missing_subjects = Subject.objects.filter(id__in=set([hier[-1].id for ps in PreprintService.objects.filter(provider=custom_provider) for hier in ps.subject_hierarchy])).exclude(id__in=included_subjects.values_list('id', flat=True))
    assert not missing_subjects.exists(), 'Incomplete mapping -- following subjects in use but not included:\n{}'.format(missing_subjects.all())
    logger.info('Successfully validated mapping completeness')

def create_subjects_recursive(custom_provider, root_text, exclude_texts, parent=None):
    logger.info('Duplicating BePress subject {} on {}'.format(root_text, custom_provider._id))
    bepress_subj = Subject.objects.get(provider=BEPRESS_PROVIDER, text=root_text)
    custom_subj = Subject(text=root_text, parent=parent, bepress_subject=bepress_subj, provider=custom_provider)
    custom_subj.save()
    # This is not a problem now, as all excluded subjects are leafs, but it could be problematic if non-leafs had their children excluded.
    # It could also be problematic if they didn't, if any of those children are used by existing preprints.
    # TODO: Determine correct resolution
    for child_text in bepress_subj.children.exclude(text__in=exclude_texts).values_list('text', flat=True):
        create_subjects_recursive(custom_provider, child_text, exclude_texts, parent=custom_subj)

def do_create_subjects(custom_provider, includes, excludes):
    for root_text in includes:
        create_subjects_recursive(custom_provider, root_text, excludes)

def map_custom_subject(custom_provider, name, parent, mapping):
    logger.info('Attempting to create subject {} on {} from {} with {}'.format(name, custom_provider._id, mapping, 'parent {}'.format(parent) if parent else 'no parent'))
    if parent:
        parent_subject = Subject.objects.filter(provider=custom_provider, text=parent).first()
    else:
        parent_subject = None
    bepress_subject = Subject.objects.get(provider=BEPRESS_PROVIDER, text=mapping)
    if parent and not parent_subject:
        return False
    custom_subject = Subject(provider=custom_provider, text=name, parent=parent_subject, bepress_subject=bepress_subject)
    custom_subject.save()
    return True

def do_custom_mapping(custom_provider, customs):
    tries = 0
    unmapped_customs = customs
    previous_len = len(unmapped_customs)
    while len(unmapped_customs):
        tries += 1
        if tries == 10:
            raise RuntimeError('Unable to map custom subjects with 10 iterations -- invalid input')
        successes = []
        for cust_name, map_dict in unmapped_customs.iteritems():
            if map_custom_subject(custom_provider, cust_name, map_dict.get('parent'), map_dict.get('bepress')):
                successes.append(cust_name)
            else:
                logger.warn('Failed. Retrying next iteration')
        [unmapped_customs.pop(key) for key in successes]
        new_len = len(unmapped_customs)
        if new_len == previous_len:
            raise RuntimeError('Unable to map any custom subjects on iteration -- invalid input')

def map_preprints_to_custom_subjects(custom_provider):
    for preprint in PreprintService.objects.filter(provider=custom_provider):
        logger.info('Preparing to migrate preprint {}'.format(preprint.id))
        old_hier = preprint.subject_hierarchy
        subject_ids_to_map = [hier[-1].id for hier in old_hier]
        aliased_subject_ids = set(Subject.objects.filter(bepress_subject__id__in=subject_ids_to_map, provider=custom_provider).values_list('id', flat=True))
        aliased_hiers = [s.object_hierarchy for s in Subject.objects.filter(id__in=aliased_subject_ids)]
        preprint.subjects.clear()
        for hier in aliased_hiers:
            validate_subject_hierarchy([s._id for s in hier])
            for s in hier:
                preprint.subjects.add(s)
        preprint.save()
        preprint.reload()
        new_hier = [s.object_hierarchy for s in preprint.subjects.exclude(children__in=preprint.subjects.all())]
        logger.info('Successfully migrated preprint {}.\n\tOld hierarchy:{}\n\tNew hierarchy:{}'.format(preprint.id, old_hier, new_hier))

def migrate(provider=None, data=None):
    custom_provider = PreprintProvider.objects.filter(_id=provider).first()
    assert custom_provider, 'Unable to find specified provider: {}'.format(provider)
    assert custom_provider.id != BEPRESS_PROVIDER.id, 'Cannot add custom mapping to BePress provider'
    validate_input(custom_provider, data)
    do_create_subjects(custom_provider, data['include'], data.get('exclude', []))
    do_custom_mapping(custom_provider, data.get('custom', {}))
    map_preprints_to_custom_subjects(custom_provider)

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
            '--data',
            action='store',
            dest='data',
            required=True,
            help='List of targets, of form {\n"include": [<list of subject texts to include at top level, children implicit>],'
            '\n"exclude": [<list of children to exclude from included trees>],'
            '\n"custom": [{"<Custom Name": {"parent": <Parent text>", "bepress": "<Bepress Name>"}}, ...]}',
        )
        parser.add_argument(
            '--provider',
            action='store',
            dest='provider',
            required=True,
            help='_id of the PreprintProvider object, e.g. "osf"'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        provider = options['provider']
        data = options['data']
        if not dry_run:
            script_utils.add_file_logger(logger, __file__)
        with transaction.atomic():
            migrate(provider=provider, data=json.loads(data))
            if dry_run:
                raise RuntimeError('Dry run, transaction rolled back.')
