import datetime
import logging

from django.core.management.base import BaseCommand
from django.db import OperationalError as DjangoOperationalError
from elasticsearch.exceptions import ConnectionError as ElasticConnectionError
from psycopg2 import OperationalError as PostgresOperationalError

from framework.celery_tasks import app as celery_app
import framework.sentry
from osf.metrics.reporters import AllMonthlyReporters
from osf.metrics.utils import YearMonth


logger = logging.getLogger(__name__)


_CONTINUE_AFTER_ERRORS = (
    DjangoOperationalError,
    ElasticConnectionError,
    PostgresOperationalError,
)

@celery_app.task(name='management.commands.monthly_reporters_go')
def monthly_reporters_go(yearmonth: str = '', reporter_key: str = ''):
    _yearmonth = (
        YearMonth.from_str(yearmonth)
        if yearmonth
        else YearMonth.from_date(datetime.date.today()).prior()  # default last month
    )
    _reporter_keys = (
        [reporter_key]
        if reporter_key
        else _enum_names(AllMonthlyReporters)
    )
    for _reporter_key in _reporter_keys:
        schedule_monthly_reporter.apply_async(kwargs={
            'yearmonth': str(_yearmonth),
            'reporter_key': _reporter_key,
        })


@celery_app.task(name='management.commands.schedule_monthly_reporter')
def schedule_monthly_reporter(
    yearmonth: str,
    reporter_key: str,
    continue_after: dict | None = None,
):
    _reporter = _get_reporter(reporter_key, yearmonth)
    _last_kwargs = None
    try:
        for _kwargs in _reporter.iter_report_kwargs(continue_after=continue_after):
            monthly_reporter_do.apply_async(kwargs={
                'yearmonth': yearmonth,
                'reporter_key': reporter_key,
                'report_kwargs': _kwargs,
            })
            _last_kwargs = _kwargs
    except _CONTINUE_AFTER_ERRORS as _error:
        # let the celery task succeed but log the error
        framework.sentry.log_exception(_error)
        # schedule another task to continue scheduling
        if _last_kwargs is not None:
            schedule_monthly_reporter.apply_async(kwargs={
                'yearmonth': yearmonth,
                'reporter_key': reporter_key,
                'continue_after': _last_kwargs,
            })


@celery_app.task(
    name='management.commands.monthly_reporter_do',
    autoretry_for=(
        DjangoOperationalError,
        ElasticConnectionError,
        PostgresOperationalError,
    ),
    max_retries=5,
    retry_backoff=True,
)
def monthly_reporter_do(reporter_key: str, yearmonth: str, report_kwargs: dict):
    try:
        _reporter = _get_reporter(reporter_key, yearmonth)
    except KeyError as exc:
        framework.sentry.log_exception(exc)
        return

    _report = _reporter.report(**report_kwargs)
    if _report is not None:
        _report.report_yearmonth = _reporter.yearmonth
        _report.save()
        _followup_task = _reporter.followup_task(_report)
        if _followup_task is not None:
            _followup_task.apply_async()


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            'yearmonth',
            type=str,
            help='year and month (YYYY-MM)',
        )
        parser.add_argument(
            '-r', '--reporter',
            type=str,
            choices={_name.lower() for _name in _enum_names(AllMonthlyReporters)},
            default='',
            help='name of the reporter to run (default all)',
        )

    def handle(self, *args, **kwargs):
        monthly_reporters_go(
            yearmonth=kwargs['yearmonth'],
            reporter_key=kwargs['reporter'].upper(),
        )
        self.stdout.write(self.style.SUCCESS(
            f'scheduling tasks for monthly reporter "{kwargs['reporter']}"...'
            if kwargs['reporter']
            else 'scheduling tasks for all monthly reporters...'
        ))


def _get_reporter(reporter_key: str, yearmonth: str):
    _reporter_class = AllMonthlyReporters[reporter_key].value
    return _reporter_class(YearMonth.from_str(yearmonth))


def _enum_names(enum_cls) -> list[str]:
    return list(enum_cls.__members__.keys())
