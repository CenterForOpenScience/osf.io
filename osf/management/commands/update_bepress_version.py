from __future__ import unicode_literals
import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from scripts import utils as script_utils
from osf.models import PreprintProvider, Subject
from website.preprints.tasks import on_preprint_updated

logger = logging.getLogger(__name__)

BEPRESS_PROVIDER = PreprintProvider.objects.filter(_id='osf').first()
BEPRESS_CHANGES = {
    'create': [
        'Education:Adult and Continuing Education',
        'Education:Disability and Equity in Education:Gender Equity in Education',
        'Education:Early Childhood Education',
        'Education:Elementary Education',
        'Education:Indigenous Education',
        'Education:Language and Literacy Education',
        'Education:Outdoor Education',
        'Education:Secondary Education',
        'Education:Vocational Education',
        'Engineering:Aviation:Aviation and Space Education',
        'Medicine and Health Sciences:Medical Education:Interprofessional Education',
        'Medicine and Health Sciences:Medical Specialties:Tropical Medicine',
        'Medicine and Health Sciences:Medical Specialties:Sleep Medicine',
        'Law:Cultural Heritage Law',
        'Life Sciences:Plant Sciences:Bryology',
        'Life Sciences:Research Methods in Life Sciences',
        'Life Sciences:Research Methods in Life Sciences:Animal Experimentation and Research',
        'Physical Sciences and Mathematics:Earth Sciences:Speleology',
        'Social and Behavioral Sciences:Food Studies',
        'Social and Behavioral Sciences:Psychology:Comparative Psychology',
        'Social and Behavioral Sciences:Psychology:Transpersonal Psychology',
        'Social and Behavioral Sciences:Public Affairs, Public Policy and Public Administration:Terrorism Studies'
    ],
    'rename': {
        'Native American Studies': 'Indigenous Studies',
        'Computer Security': 'Information Security',
        'Military Studies': 'Military and Veterans Studies',
    }
}

def update(dry_run=False):
    created_dict = {'osf': []}
    for hier in BEPRESS_CHANGES['create']:
        new_text = hier.split(':')[-1]
        bepress_parent = BEPRESS_PROVIDER.subjects.get(text=hier.split(':')[-2])
        logger.info('Creating osf - {}'.format(new_text))
        bepress_subject = Subject.objects.create(parent=bepress_parent, provider=BEPRESS_PROVIDER, text=new_text)
        created_dict['osf'].append(new_text)
        for custom_parent in bepress_parent.aliases.all():
            if not bepress_parent.children.count() > 1 or (
                    custom_parent.children.exists() and
                    set(bepress_parent.children.exclude(text=new_text).values_list('text', flat=True)).issubset(set(custom_parent.children.values_list('text', flat=True)))):
                # Either children were included in the custom taxonomy or they didn't exist before, probably
                logger.info('Creating {} - {}'.format(custom_parent.provider._id, new_text))
                Subject.objects.create(parent=custom_parent, provider=custom_parent.provider, text=new_text, bepress_subject=bepress_subject)
                if custom_parent.provider._id not in created_dict:
                    created_dict[custom_parent.provider._id] = []
                created_dict[custom_parent.provider._id].append(new_text)
    for old, new in BEPRESS_CHANGES['rename'].items():
        logger.info('Renaming `{}`->`{}`'.format(old, new))
        to_update = Subject.objects.filter(text=old)
        affected_preprints = set(to_update.exclude(preprints__isnull=True).values_list('preprints__guids___id', flat=True))
        to_update.update(text=new)
        for preprint_id in affected_preprints:
            logger.info('Notifying SHARE about preprint {} change'.format(preprint_id))
            if not dry_run:
                on_preprint_updated(preprint_id)
    for provider_id, list_of_subjs in created_dict.items():
        logger.info('Created {} new subjects on {}: "{}"'.format(len(list_of_subjs), provider_id, ', '.join(list_of_subjs)))


class Command(BaseCommand):
    """
    Add/Rename subjects based on BePress taxonomy changes, update SHARE with new data for affected preprints
    """
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Migrate data then roll back',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        if not dry_run:
            script_utils.add_file_logger(logger, __file__)
        with transaction.atomic():
            update(dry_run)
            if dry_run:
                raise RuntimeError('Dry run -- transaction rolled back')
