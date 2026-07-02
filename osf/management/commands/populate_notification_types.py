import sys
import yaml
from waffle import switch_is_active
from osf import features

from django.db.utils import ProgrammingError
from website import settings

import logging
from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)

FREQ_MAP = {
    'none': 'none',
    'email_digest': 'weekly',
    'email_transactional': 'instantly',
}

def populate_notification_types(*args, restore_one=None, restore_all=False, **kwargs):
    if kwargs.get('sender'):  # exists when called as a post_migrate signal
        if not switch_is_active(features.POPULATE_NOTIFICATION_TYPES):
            if 'pytest' not in sys.modules:
                logger.info('POPULATE_NOTIFICATION_TYPES switch is off; skipping population of notification types.')
                return
    logger.info('Populating notification types...')
    from django.contrib.contenttypes.models import ContentType
    from osf.models.notification_type import NotificationType

    try:
        with open(settings.NOTIFICATION_TYPES_YAML) as stream:
            notification_types = yaml.safe_load(stream)

        notification_types_dict = {
            nt['name']: nt for nt in notification_types['notification_types']
        }

        all_names = set(notification_types_dict.keys())
        existing_names = set(
            NotificationType.objects.values_list('name', flat=True)
        )

        if restore_one:
            if restore_one not in notification_types_dict:
                raise ValueError(f'Notification type "{restore_one}" not found in YAML')
            names_to_process = {restore_one}

        elif restore_all:
            names_to_process = all_names

        else:
            names_to_process = all_names - existing_names

        logger.info(f'Processing {len(names_to_process)} notification types')

        for name in names_to_process:
            raw_nt = notification_types_dict[name].copy()

            raw_nt.pop('__docs__', None)
            raw_nt.pop('tests', None)

            object_content_type_model_name = raw_nt.pop('object_content_type_model_name')

            if object_content_type_model_name == 'desk':
                content_type = None
            else:
                try:
                    content_type = ContentType.objects.get_by_natural_key(app_label='osf', model=object_content_type_model_name)
                except ContentType.DoesNotExist:
                    raise ValueError(f'No content type for osf.{object_content_type_model_name}')

            template_path = raw_nt.pop('template')
            template = None

            if template_path:
                with open(template_path) as stream:
                    template = stream.read()

            nt, _ = NotificationType.objects.update_or_create(
                name=name,
                defaults=raw_nt,
            )

            nt.object_content_type = content_type
            if template:
                nt.template = template

            nt.save()

    except ProgrammingError:
        logger.info('Notification types failed potential side effect of reverse migration')
    logger.info('Finished populating notification types.')

class Command(BaseCommand):
    help = 'Populate notification types.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--restore-all',
            action='store_true',
            help='Restore all templates from files'
        )
        parser.add_argument(
            '--restore',
            type=str,
            help='Restore specific template by name'
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            populate_notification_types(
                restore_all=options['restore_all'],
                restore_one=options['restore']
            )
