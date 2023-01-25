from datetime import timedelta
import logging
import re

from django.core.management.base import BaseCommand
from django.utils import timezone

from framework import sentry
from framework.celery_tasks import app as celery_app
from osf.metrics.reporters import MONTHLY_REPORTERS
from osf.metrics.reporters.utils import YearMonth
from website.app import init_app


logger = logging.getLogger(__name__)


MAXMONTH = 12


@celery_app.task(name='management.commands.monthly_reporters_go')
def monthly_reporters_go(report_year=None, report_month=None):
    init_app()  # OSF-specific setup

    if report_year is None and report_month is None:
        # default to last month
        today = timezone.now().date()
        if today.month == 1:
            report_yearmonth = YearMonth(
                year=today.year - 1,
                month=MAXMONTH,
            )
        else:
            report_yearmonth = YearMonth(
                year=today.year,
                month=today.month - 1,
            )
    else:
        assert report_year and report_month
        report_yearmonth = YearMonth(report_year, report_month)

    errors = {}
    for reporter_class in MONTHLY_REPORTERS:
        try:
            reporter_class().run_and_record_for_month(report_yearmonth)
        except Exception as e:
            errors[reporter_class.__name__] = str(e)
            logger.exception(e)
            sentry.log_exception()
            # continue with the next reporter
    return errors


def parse_yearmonth(input_str):
    match = re.fullmatch(r'(?P<year>\d{4})-(?P<month>\d{2})', input_str)
    if match:
        return {
            'year': int(match.group('year')),
            'month': int(match.group('month')),
        }
    else:
        raise ValueError(f'could not parse yearmonth (expected "YYYY-MM"), got "{input_str}"')


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            'yearmonth',
            type=parse_yearmonth,
            default={'year': None, 'month': None},
            help='year and month (YYYY-MM)',
        )
    def handle(self, *args, **options):
        errors = monthly_reporters_go(
            report_date=options.get('date'),
        )
        for error_key, error_val in errors:
            self.stdout.write(self.style.ERROR(f'error running {error_key}: ') + error_val)
        self.stdout.write(self.style.SUCCESS('done.'))
