import datetime
import logging

from django.core.management.base import BaseCommand
from django.db.utils import OperationalError
from django.utils import timezone

from framework.celery_tasks import app as celery_app
from osf.metrics.reporters import AllDailyReporters
from website.app import init_app


logger = logging.getLogger(__name__)


@celery_app.task(name='management.commands.daily_reporters_go')
def daily_reporters_go(also_send_to_keen=False, report_date=None, reporter_filter=None):
    init_app()  # OSF-specific setup

    if report_date is None:  # default to yesterday
        report_date = (timezone.now() - datetime.timedelta(days=1)).date()

    for _reporter_key, _reporter_class in AllDailyReporters.__members__.items():
        if reporter_filter and (reporter_filter.lower() not in _reporter_class.__name__.lower()):
            continue
        daily_reporter_go.apply_async(kwargs={
            'reporter_key': _reporter_key,
            'report_date': report_date.isoformat(),
        })


@celery_app.task(
    name='management.commands.daily_reporter_go',
    autoretry_for=(OperationalError,),
    max_retries=5,
    retry_backoff=True,
    bind=True,
)
def daily_reporter_go(task, reporter_key: str, report_date: str):
    _reporter_class = AllDailyReporters[reporter_key].value
    _parsed_date = datetime.date.fromisoformat(report_date)
    _reporter_class().run_and_record_for_date(report_date=_parsed_date)


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
            type=datetime.date.fromisoformat,
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
