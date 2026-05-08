import datetime
import logging

from django.core.management.base import BaseCommand
from django.db.utils import OperationalError
from django.utils import timezone

from framework.celery_tasks import app as celery_app
from osf.metrics.reporters import AllDailyReporters


logger = logging.getLogger(__name__)


@celery_app.task(name='management.commands.daily_reporters_go')
def daily_reporters_go(report_date=None, reporter_key=None, **kwargs):
    if not report_date:  # default to yesterday
        report_date = (timezone.now() - datetime.timedelta(days=1)).date()
    _reporter_keys = (
        [reporter_key]
        if reporter_key
        else AllDailyReporters.__members__.keys()
    )
    for _reporter_key in _reporter_keys:
        daily_reporter_go.apply_async(kwargs={
            'reporter_key': _reporter_key,
            'report_date': report_date if isinstance(report_date, str) else report_date.isoformat(),
        })


@celery_app.task(
    name='management.commands.daily_reporter_go',
    autoretry_for=(OperationalError,),
    max_retries=5,
    retry_backoff=True,
    bind=True,
)
def daily_reporter_go(task, reporter_key: str, report_date: str):
    _reporter_class = AllDailyReporters[reporter_key.upper()].value
    _parsed_date = datetime.date.fromisoformat(report_date)
    _reporter_class().run_and_record_for_date(report_date=_parsed_date)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=datetime.date.fromisoformat,
            help='run for a specific date (default: yesterday)',
        )
        parser.add_argument(
            '-r', '--reporter',
            type=str,
            choices={_enum.name.lower() for _enum in AllDailyReporters},
            default='',
            help='name of the reporter to run (default all)',
        )
    def handle(self, *args, **options):
        _report_date = options.get('date')
        daily_reporters_go.delay(
            report_date=_report_date.isoformat() if _report_date else None,
            reporter_key=options.get('reporter'),
        )
        self.stdout.write(self.style.SUCCESS('daily reporters going...'))
