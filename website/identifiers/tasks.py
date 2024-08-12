import logging
from django.apps import apps

from framework.celery_tasks import app as celery_app
from framework.celery_tasks.handlers import queued_task
from framework import sentry


@celery_app.task(bind=True, max_retries=5, acks_late=True)
def task__update_doi_metadata_on_change(self, target_guid):
    sentry.log_message(
        "Updating DOI for guid",
        extra_data={"guid": target_guid},
        level=logging.INFO,
    )
    Guid = apps.get_model("osf.Guid")
    target_object = Guid.load(target_guid).referent
    if target_object.get_identifier("doi"):
        target_object.request_identifier_update(category="doi")


@queued_task
@celery_app.task(ignore_results=True)
def update_doi_metadata_on_change(target_guid):
    task__update_doi_metadata_on_change(target_guid)
