from framework.celery_tasks import app as celery_app
from django.apps import apps
from django.utils import timezone

from website import settings
from osf.external.chronos import ChronosClient
import logging

logger = logging.getLogger(__name__)


@celery_app.task(ignore_results=True)
def update_submissions_status_async(ids):
    client = ChronosClient()
    ChronosSubmission = apps.get_model('osf.ChronosSubmission')
    for submission_id in ids:
        submission = ChronosSubmission.load(submission_id)
        if submission.modified < timezone.now() - settings.CHRONOS_SUBMISSION_UPDATE_TIME:
            client.sync_manuscript(submission)
