import logging

from django.apps import apps
from django.conf import settings
from django.db import transaction

from framework.celery_tasks import app

logger = logging.getLogger(__name__)


@app.task(max_retries=5, default_retry_delay=60)
def purge_file_version_task(version_pk):

    from google.cloud.storage.client import Client
    from google.oauth2.service_account import Credentials

    FileVersion = apps.get_model('osf.FileVersion')
    with transaction.atomic():
        version = FileVersion.objects.filter(pk=version_pk).first()
        if not version or version.purged:
            return 0

        creds_path = getattr(settings, 'GCS_CREDS', None)
        if not creds_path:
            logger.error(f'GCS_CREDS not configured; cannot purge FileVersion {version_pk}')
            return 0

        creds = Credentials.from_service_account_file(creds_path)
        client = Client(credentials=creds)
        return version._purge(client=client)
