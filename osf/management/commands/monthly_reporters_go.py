import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from framework import sentry
from framework.celery_tasks import app as celery_app
from osf.metrics.reporters import MONTHLY_REPORTERS
from osf.metrics.utils import YearMonth
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


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            'yearmonth',
            type=YearMonth.from_str,
            default={'year': None, 'month': None},
            help='year and month (YYYY-MM)',
        )

    def handle(self, *args, **options):
        errors = monthly_reporters_go(
            report_year=getattr(options.get('yearmonth'), 'year', None),
            report_month=getattr(options.get('yearmonth'), 'month', None),
        )
        for error_key, error_val in errors.items():
            self.stdout.write(self.style.ERROR(f'error running {error_key}: ') + error_val)
        self.stdout.write(self.style.SUCCESS('done.'))