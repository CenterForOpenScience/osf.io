# -*- coding: utf-8 -*-
import os
import json
import logging

from django.core.management.base import BaseCommand

from website import settings
from osf.models import AbstractProvider, Subject

logger = logging.getLogger(__name__)


def main(provider_id):
    provider = AbstractProvider.objects.get(_id=provider_id)

    assert provider.subjects.count() == 0, 'This provider already has a custom taxonomy'

    # Flat taxonomy is stored locally, read in here
    with open(os.path.join(settings.APP_PATH, 'website', 'static', 'bepress_taxonomy.json')) as fp:
        taxonomy = json.load(fp)

    for subject_path in taxonomy.get('data'):
        subjects = subject_path.split('_')
        text = subjects[-1]

        parent = None
        if len(subjects) > 1:
            parent, _ = Subject.objects.get_or_create(text=subjects[-2], provider=provider)
        subject, _ = Subject.objects.get_or_create(text=text, provider=provider)
        if parent and not subject.parent:
            subject.parent = parent
            subject.save()


class Command(BaseCommand):
    """Ensure all features and switches are updated with the switch and flag files
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '-id',
            type=str,
            help='The id of the provider who\'s taxonomy you want to make custom'
        )

    def handle(self, *args, **options):
        provider_id = options.get('id', False)
        main(provider_id)
