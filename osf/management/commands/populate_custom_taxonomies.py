import json
import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from osf.models import PreprintProvider, PreprintService, Subject
from osf.models.provider import rules_to_subjects
from scripts import utils as script_utils
from osf.models.validators import validate_subject_hierarchy
from website.preprints.tasks import on_preprint_updated

logger = logging.getLogger(__name__)

BEPRESS_PROVIDER = None

def validate_input(custom_provider, data, copy=False, add_missing=False):

    # This function may be run outside of this command (e.g. in the admin app) so we
    # need to make sure that BEPRESS_PROVIDER is set
    global BEPRESS_PROVIDER
    BEPRESS_PROVIDER = PreprintProvider.objects.filter(_id='osf').first()

    logger.info('Validating data')
    includes = data.get('include', [])
    excludes = data.get('exclude', [])
    customs = data.get('custom', {})
    merges = data.get('merge', {})
    if copy:
        included_subjects = rules_to_subjects(custom_provider.subjects_acceptable)
    else:
        assert not set(includes) & set(excludes), 'There must be no overlap between includes and excludes'
        for text in includes:
            assert Subject.objects.filter(provider=BEPRESS_PROVIDER, text=text).exists(), 'Unable to find included subject with text {}'.format(text)
        included_subjects = Subject.objects.filter(provider=BEPRESS_PROVIDER, text__in=includes).include_children()
        logger.info('Successfully validated `include`')
        for text in excludes:
            try:
                Subject.objects.get(provider=BEPRESS_PROVIDER, text=text)
            except Subject.DoesNotExist:
                raise RuntimeError('Unable to find excluded subject with text {}'.format(text))
            assert included_subjects.filter(text=text).exists(), 'Excluded subject with text {} was not included'.format(text)
        included_subjects = included_subjects.exclude(text__in=excludes)
        logger.info('Successfully validated `exclude`')
    for cust_name, map_dict in customs.iteritems():
        assert not included_subjects.filter(text=cust_name).exists(), 'Custom text {} already exists in mapped set'.format(cust_name)
        assert Subject.objects.filter(provider=BEPRESS_PROVIDER, text=map_dict.get('bepress')).exists(), 'Unable to find specified BePress subject with text {}'.format(map_dict.get('bepress'))
        if map_dict.get('parent'):  # Null parent possible
            assert map_dict['parent'] in set(customs.keys()) | set(included_subjects.values_list('text', flat=True)), 'Unable to find specified parent with text {} in mapped set'.format(map_dict['parent'])
            # TODO: hierarchy length validation? Probably more trouble than worth here, done on .save
    logger.info('Successfully validated `custom`')
    included_subjects = included_subjects | Subject.objects.filter(text__in=[map_dict['bepress'] for map_dict in customs.values()])
    for merged_from, merged_into in merges.iteritems():
        assert not included_subjects.filter(text=merged_from).exists(), 'Cannot merge subject "{}" that will be included'.format(merged_from)
        assert merged_into in set(included_subjects.values_list('text', flat=True)) | set(customs.keys()), 'Unable to determine merge target for "{}"'.format(merged_into)
    included_subjects = included_subjects | Subject.objects.filter(text__in=merges.keys())
    missing_subjects = Subject.objects.filter(id__in=set([hier[-1].id for ps in PreprintService.objects.filter(provider=custom_provider) for hier in ps.subject_hierarchy])).exclude(id__in=included_subjects.values_list('id', flat=True))
    if not add_missing:
        assert not missing_subjects.exists(), 'Incomplete mapping -- following subjects in use but not included:\n{}'.format(list(missing_subjects.values_list('text', flat=True)))
    assert custom_provider.share_title not in [None, '', 'bepress'], 'share title not set; please set the share title on this provider before creating a custom taxonomy.'

    logger.info('Successfully validated mapping completeness')
    return list(missing_subjects) if add_missing else None

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

def create_from_subjects_acceptable(custom_provider, add_missing=False, missing=None):
    tries = 0
    subjects_to_copy = list(rules_to_subjects(custom_provider.subjects_acceptable))
    if missing and add_missing:
        subjects_to_copy = subjects_to_copy + missing
    while len(subjects_to_copy):
        previous_len = len(subjects_to_copy)
        tries += 1
        if tries == 10:
            raise RuntimeError('Unable to map subjects acceptable with 10 iterations -- subjects remaining: {}'.format(subjects_to_copy))
        for subj in list(subjects_to_copy):
            if map_custom_subject(custom_provider, subj.text, subj.parent.text if subj.parent else None, subj.text):
                subjects_to_copy.remove(subj)
            elif add_missing and subj.parent and subj.parent not in subjects_to_copy:
                # Dirty
                subjects_to_copy.append(subj.parent)
                previous_len += 1
            else:
                logger.warn('Failed. Retrying next iteration')
        new_len = len(subjects_to_copy)
        if new_len == previous_len:
            raise RuntimeError('Unable to map any custom subjects on iteration -- subjects remaining: {}'.format(subjects_to_copy))


def do_create_subjects(custom_provider, includes, excludes, copy=False, add_missing=False, missing=None):
    if copy:
        create_from_subjects_acceptable(custom_provider, add_missing=add_missing, missing=missing)
    else:
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
    while len(unmapped_customs):
        previous_len = len(unmapped_customs)
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

def map_preprints_to_custom_subjects(custom_provider, merge_dict, dry_run=False):
    for preprint in PreprintService.objects.filter(provider=custom_provider):
        logger.info('Preparing to migrate preprint {}'.format(preprint.id))
        old_hier = preprint.subject_hierarchy
        subjects_to_map = [hier[-1] for hier in old_hier]
        merged_subject_ids = set(Subject.objects.filter(provider=custom_provider, text__in=[merge_dict[k] for k in set(merge_dict.keys()) & set([s.text for s in subjects_to_map])]).values_list('id', flat=True))
        subject_ids_to_map = set(s.id for s in subjects_to_map if s.text not in merge_dict.keys())
        aliased_subject_ids = set(Subject.objects.filter(bepress_subject__id__in=subject_ids_to_map, provider=custom_provider).values_list('id', flat=True)) | merged_subject_ids
        aliased_hiers = [s.object_hierarchy for s in Subject.objects.filter(id__in=aliased_subject_ids)]
        old_subjects = list(preprint.subjects.values_list('id', flat=True))
        preprint.subjects.clear()
        for hier in aliased_hiers:
            validate_subject_hierarchy([s._id for s in hier])
            for s in hier:
                preprint.subjects.add(s)
        # Update preprint in SHARE
        if not dry_run:
            on_preprint_updated(preprint._id, old_subjects=old_subjects, update_share=True)
        preprint.reload()
        new_hier = [s.object_hierarchy for s in preprint.subjects.exclude(children__in=preprint.subjects.all())]
        logger.info('Successfully migrated preprint {}.\n\tOld hierarchy:{}\n\tNew hierarchy:{}'.format(preprint.id, old_hier, new_hier))

def migrate(provider=None, share_title=None, data=None, dry_run=False, copy=False, add_missing=False):
    # This function may be run outside of this command (e.g. in the admin app) so we
    # need to make sure that BEPRESS_PROVIDER is set
    global BEPRESS_PROVIDER
    if not BEPRESS_PROVIDER:
        BEPRESS_PROVIDER = PreprintProvider.objects.filter(_id='osf').first()
    custom_provider = PreprintProvider.objects.filter(_id=provider).first()
    assert custom_provider, 'Unable to find specified provider: {}'.format(provider)
    assert custom_provider.id != BEPRESS_PROVIDER.id, 'Cannot add custom mapping to BePress provider'
    assert not custom_provider.subjects.exists(), 'Provider aldready has a custom taxonomy'
    if custom_provider.share_title in [None, '', 'bepress']:
        if not share_title:
            raise RuntimeError('`--share-title` is required if not already set on the provider')
        custom_provider.share_title = share_title
        custom_provider.save()
    missing = validate_input(custom_provider, data, copy=copy, add_missing=add_missing)
    do_create_subjects(custom_provider, data['include'], data.get('exclude', []), copy=copy, add_missing=add_missing, missing=missing)
    do_custom_mapping(custom_provider, data.get('custom', {}))
    map_preprints_to_custom_subjects(custom_provider, data.get('merge', {}), dry_run=dry_run)

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
            help='List of targets, of form {\n"include": [<list of subject texts to include at top level, children implicit>],'
            '\n"exclude": [<list of children to exclude from included trees>],'
            '\n"custom": [{"<Custom Name": {"parent": <Parent text>", "bepress": "<Bepress Name>"}}, ...]'
            '\n"merge": {"<Merged from (bepress)>": "<Merged into (custom)", ...}}',
        )
        parser.add_argument(
            '--provider',
            action='store',
            dest='provider',
            required=True,
            help='_id of the PreprintProvider object, e.g. "osf". Provider is expected to not already have a custom taxonomy.'
        )
        parser.add_argument(
            '--from-subjects-acceptable',
            action='store_true',
            dest='from_subjects_acceptable',
            help='Specifies that the provider\'s `subjects_acceptable` be copied. `data.include` and `exclude` are ignored, the other keys may still be used'
        )
        parser.add_argument(
            '--add-missing',
            action='store_true',
            dest='add_missing',
            help='Adds "used-but-not-included" subjects.'
        )
        parser.add_argument(
            '--share-title',
            action='store',
            type=str,
            dest='share_title',
            help='Sets <provider>.share_title. Ignored if already set on provider, required if not.'
        )

    def handle(self, *args, **options):
        global BEPRESS_PROVIDER
        BEPRESS_PROVIDER = PreprintProvider.objects.filter(_id='osf').first()
        dry_run = options.get('dry_run')
        provider = options['provider']
        data = json.loads(options['data'] or '{}')
        share_title = options.get('share_title')
        copy = options.get('from_subjects_acceptable')
        add_missing = options.get('add_missing')
        if copy:
            data['include'] = list(Subject.objects.filter(provider=BEPRESS_PROVIDER, parent__isnull=True).values_list('text', flat=True))
        if not dry_run:
            script_utils.add_file_logger(logger, __file__)
        with transaction.atomic():
            migrate(provider=provider, share_title=share_title, data=data, dry_run=dry_run, copy=copy, add_missing=add_missing)
            if dry_run:
                raise RuntimeError('Dry run, transaction rolled back.')
