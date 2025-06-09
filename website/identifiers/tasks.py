import logging
from django.apps import apps

from osf.external.gravy_valet.exceptions import GVException
from framework.celery_tasks import app as celery_app
from framework.celery_tasks.handlers import queued_task
from framework import sentry

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=5, acks_late=True)
def task__update_doi_metadata_on_change(self, target_guid):
    sentry.log_message('Updating DOI for guid', extra_data={'guid': target_guid}, level=logging.INFO)
    Guid = apps.get_model('osf.Guid')
    target_object = Guid.load(target_guid).referent
    if target_object.get_identifier('doi'):
        target_object.request_identifier_update(category='doi')

@queued_task
@celery_app.task(ignore_results=True)
def update_doi_metadata_on_change(target_guid):
    task__update_doi_metadata_on_change(target_guid)

@celery_app.task(bind=True, max_retries=5, acks_late=True)
def task__update_verified_links(self, target_guid):
    logger.debug(f'Updating DOI metadata for guid due to verified links configuration change in Gravy Valet: '
                 f'[guid={target_guid}]')

    Guid = apps.get_model('osf.Guid')
    target_object = Guid.load(target_guid).referent
    try:
        target_object.request_identifier_update(category='doi')
        sentry.log_message(
            'DOI metadata with verified links updated for guid',
            extra_data={'guid': target_guid},
            level=logging.INFO
        )
        logger.debug(f'DOI metadata for guid with verified links updated: [guid={target_guid}]')
    except Exception as e:
        sentry.log_message(
            'Failed to update DOI metadata with verified links',
            extra_data={'guid': target_guid, 'error': str(e)},
            level=logging.ERROR
        )
        logger.error(f'DOI metadata for guid with verified links failed to update: [guid={target_guid}]')
        raise self.retry(exc=e)

    try:
        target_object.update_search()
    except GVException as e:
        logger.error(f'Share update for guid with verified links failed to update: [guid={target_guid}]')
        raise self.retry(exc=e)


@queued_task
@celery_app.task(ignore_results=True)
def update_verified_links(target_guid):
    # TODO: log sentry if fails after max retry
    task__update_verified_links(target_guid)
