#!/usr/bin/env python3
import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from osf.models.mixins import ReviewProviderMixin

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Add/update reviews auth groups for all reviews providers"""
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Run, then roll back changes to db',
        )

    def handle(self, *args, **options):
        dry = options.get('dry_run')

        # Start a transaction that will be rolled back if any exceptions are raised
        with transaction.atomic():
            for cls in ReviewProviderMixin.__subclasses__():
                for provider in cls.objects.all():
                    logger.info('Updating auth groups for review provider %s', provider)
                    provider.update_group_permissions()
            if dry:
                # When running in dry mode force the transaction to rollback
                raise Exception('Abort Transaction - Dry Run')
