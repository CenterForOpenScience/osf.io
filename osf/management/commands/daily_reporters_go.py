from datetime import timedelta
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from framework import sentry
from framework.celery_tasks import app as celery_app
from osf.metrics.reporters import DAILY_REPORTERS
from website.app import init_app


logger = logging.getLogger(__name__)


@celery_app.task(name='management.commands.daily_reporters_go')
def daily_reporters_go(also_send_to_keen=False, report_date=None):
    init_app()  # OSF-specific setup

    if report_date is None:
        # default: yesterday
        report_date = (timezone.now() - timedelta(days=1)).date()

    errors = {}
    for reporter_class in DAILY_REPORTERS:
        try:
            reporter_class().run_and_record_for_date(
                report_date=report_date,
                also_send_to_keen=also_send_to_keen,
            )
        except Exception as e:
            errors[reporter_class.__name__] = str(e)
            logger.exception(e)
            sentry.log_exception()
            # continue with the next reporter
    return errors


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--keen',
            type=bool,
            default=False,
            help='also send reports to keen',
        )
    def handle(self, *args, **options):
        daily_reporters_go(also_send_to_keen=options['keen'])
