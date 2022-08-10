from django.apps import apps

from framework.celery_tasks import app as celery_app
from framework.celery_tasks.handlers import queued_task
from framework import sentry


@queued_task
@celery_app.task(ignore_results=True)
def update_doi_metadata_on_change(target_guid):
    sentry.log_message(f'Updating DOI for [{target_guid}]')
    Guid = apps.get_model('osf.Guid')
    target_object = Guid.load(target_guid).referent
    if target_object.get_identifier('doi'):
        target_object.request_identifier_update(category='doi')
