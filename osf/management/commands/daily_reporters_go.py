import datetime
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from framework import sentry
from framework.celery_tasks import app as celery_app
from osf.metrics.reporters import DAILY_REPORTERS
from website.app import init_app


logger = logging.getLogger(__name__)


@celery_app.task(name='management.commands.daily_reporters_go')
def daily_reporters_go(also_send_to_keen=False, report_date=None, reporter_filter=None):
    init_app()  # OSF-specific setup

    if report_date is None:  # default to yesterday
        report_date = (timezone.now() - datetime.timedelta(days=1)).date()

    errors = {}
    for reporter_class in DAILY_REPORTERS:
        if reporter_filter and (reporter_filter.lower() not in reporter_class.__name__.lower()):
            continue
        try:
            reporter_class().run_and_record_for_date(
                report_date=report_date,
                also_send_to_keen=also_send_to_keen,
            )
        except Exception as e:
            errors[reporter_class.__name__] = repr(e)
            logger.exception(e)
            sentry.log_exception(e)
            # continue with the next reporter
    return errors


def date_fromisoformat(date_str):
    return datetime.datetime.strptime(date_str, '%Y-%m-%d').date()


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--keen',
            type=bool,
            default=False,
            help='also send reports to keen',
        )
        parser.add_argument(
            '--date',
            type=date_fromisoformat,  # in python 3.7+, could pass datetime.date.fromisoformat
            help='run for a specific date (default: yesterday)',
        )
        parser.add_argument(
            '--filter',
            type=str,
            help='filter by reporter name (by partial case-insensitive match)'
        )
    def handle(self, *args, **options):
        errors = daily_reporters_go(
            report_date=options.get('date'),
            also_send_to_keen=options['keen'],
            reporter_filter=options.get('filter'),
        )
        for error_key, error_val in errors.items():
            self.stdout.write(self.style.ERROR(f'error running {error_key}: ') + error_val)
        self.stdout.write(self.style.SUCCESS('done.'))
