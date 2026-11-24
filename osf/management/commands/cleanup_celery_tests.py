"""Explicit, bounded cleanup of terminal synthetic-test history."""
from datetime import timedelta

from website import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from osf.models.celery_test import CeleryTestSuite as Suite, CeleryTestTask as Task


class Command(BaseCommand):
    help = 'Delete terminal Celery test suites older than the retention period.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=settings.CELERY_STRESS_TEST_RETENTION_DAYS)
        parser.add_argument('--limit', type=int, default=100)

    def handle(self, *args, **options):
        if options['days'] < 1 or options['limit'] < 1:
            raise CommandError('Days and limit must be positive.')
        cutoff = timezone.now() - timedelta(days=options['days'])
        ids = list(Suite.objects.exclude(status__in=Suite.ACTIVE_STATUSES).filter(
            finished_at__lt=cutoff).values_list('id', flat=True)[:options['limit']])
        deleted = 0
        for suite_id in ids:
            while True:
                with transaction.atomic():
                    suite = Suite.objects.select_for_update().filter(pk=suite_id, finished_at__lt=cutoff).first()
                    if not suite or suite.is_active:
                        break
                    batch = list(suite.tasks.values_list('id', flat=True)[:200])
                    if not batch:
                        suite.delete()
                        deleted += 1
                        break
                    Task.objects.filter(id__in=batch).delete()
        self.stdout.write(f'Deleted {deleted} expired Celery test suites.')
