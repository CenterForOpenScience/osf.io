import yaml
from django.apps import apps

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

def populate_notification_types(*args, **kwargs):
    from django.contrib.contenttypes.models import ContentType
    from osf.models.notification_type import NotificationType
    try:
        with open(settings.NOTIFICATION_TYPES_YAML) as stream:
            notification_types = yaml.safe_load(stream)
        for notification_type in notification_types['notification_types']:
            notification_type.pop('__docs__', None)
            notification_type.pop('tests', None)
            object_content_type_model_name = notification_type.pop('object_content_type_model_name')

            if object_content_type_model_name == 'desk':
                content_type = None
            elif object_content_type_model_name == 'osfuser':
                OSFUser = apps.get_model('osf', 'OSFUser')
                content_type = ContentType.objects.get_for_model(OSFUser)
            elif object_content_type_model_name == 'preprint':
                Preprint = apps.get_model('osf', 'Preprint')
                content_type = ContentType.objects.get_for_model(Preprint)
            elif object_content_type_model_name == 'collectionsubmission':
                CollectionSubmission = apps.get_model('osf', 'CollectionSubmission')
                content_type = ContentType.objects.get_for_model(CollectionSubmission)
            elif object_content_type_model_name == 'abstractprovider':
                AbstractProvider = apps.get_model('osf', 'abstractprovider')
                content_type = ContentType.objects.get_for_model(AbstractProvider)
            elif object_content_type_model_name == 'osfuser':
                OSFUser = apps.get_model('osf', 'OSFUser')
                content_type = ContentType.objects.get_for_model(OSFUser)
            elif object_content_type_model_name == 'draftregistration':
                DraftRegistration = apps.get_model('osf', 'DraftRegistration')
                content_type = ContentType.objects.get_for_model(DraftRegistration)
            else:
                try:
                    content_type = ContentType.objects.get(
                        app_label='osf',
                        model=object_content_type_model_name
                    )
                except ContentType.DoesNotExist:
                    raise ValueError(f'No content type for osf.{object_content_type_model_name}')

            template_path = notification_type.pop('template')
            if template_path:
                with open(template_path) as stream:
                    template = stream.read()

            nt, _ = NotificationType.objects.update_or_create(
                name=notification_type['name'],
                defaults=notification_type,
            )
            nt.object_content_type = content_type
            if not nt.template or settings.DEV_MODE:
                nt.template = template
            nt.save()
    except ProgrammingError:
        logger.info('Notification types failed potential side effect of reverse migration')


class Command(BaseCommand):
    help = 'Population notification types.'

    def handle(self, *args, **options):
        with transaction.atomic():
            populate_notification_types(args, options)
