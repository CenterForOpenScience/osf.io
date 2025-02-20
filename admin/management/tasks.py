import logging

from framework.celery_tasks import app as celery_app
from osf.models import Preprint, Registration


logger = logging.getLogger(__name__)


@celery_app.task()
def resync_crossref():
    for preprint in Preprint.objects.exclude(article_doi=None):
        preprint.request_identifier_update('doi', create=True)


@celery_app.task()
def resync_datacite():
    for registration in Registration.objects.exclude(article_doi=None):
        registration.request_identifier_update('doi', create=True)
