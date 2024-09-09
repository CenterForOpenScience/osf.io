import logging

from django.core.management.base import BaseCommand
from django.db.utils import OperationalError
from django.utils import timezone

from framework.celery_tasks import app as celery_app
from osf.metrics.reporters import AllMonthlyReporters
from osf.metrics.utils import YearMonth
from website.app import init_app


logger = logging.getLogger(__name__)


MAXMONTH = 12


@celery_app.task(name='management.commands.monthly_reporters_go')
def monthly_reporters_go(report_year=None, report_month=None):
    init_app()  # OSF-specific setup

    if report_year and report_month:
        report_yearmonth = YearMonth(report_year, report_month)
    else:  # default to last month if year and month not provided
        today = timezone.now().date()
        report_yearmonth = YearMonth(
            year=today.year if today.month > 1 else today.year - 1,
            month=today.month - 1 or MAXMONTH,
        )
    for _reporter_key in AllMonthlyReporters.__members__.keys():
        monthly_reporter_go.apply_async(kwargs={
            'reporter_key': _reporter_key,
            'yearmonth': str(report_yearmonth),
        })


@celery_app.task(
    name='management.commands.monthly_reporter_go',
    autoretry_for=(OperationalError,),
    max_retries=5,
    retry_backoff=True,
    bind=True,
)
def monthly_reporter_go(task, reporter_key: str, yearmonth: str):
    _reporter_class = AllMonthlyReporters[reporter_key].value
    _parsed_yearmonth = YearMonth.from_str(yearmonth)
    _reporter_class().run_and_record_for_month(_parsed_yearmonth)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            'yearmonth',
            type=YearMonth.from_str,
            default={'year': None, 'month': None},
            help='year and month (YYYY-MM)',
        )

    def handle(self, *args, **options):
        monthly_reporters_go(
            report_year=getattr(options.get('yearmonth'), 'year', None),
            report_month=getattr(options.get('yearmonth'), 'month', None),
        )
        self.stdout.write(self.style.SUCCESS('reporter tasks scheduled.'))
