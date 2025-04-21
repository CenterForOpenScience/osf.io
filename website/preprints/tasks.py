import logging

from framework import sentry
from framework.exceptions import HTTPError
from framework.celery_tasks import app as celery_app
from framework.postcommit_tasks.handlers import enqueue_postcommit_task, get_task_from_postcommit_queue


CROSSREF_FAIL_RETRY_DELAY = 12 * 60 * 60
logger = logging.getLogger(__name__)


@celery_app.task(ignore_results=True, max_retries=5, default_retry_delay=60)
def on_preprint_updated(preprint_id, saved_fields=None, **kwargs):
    # WARNING: Only perform Read-Only operations in an asynchronous task, until Repeatable Read/Serializable
    # transactions are implemented in View and Task application layers.
    from osf.models import Preprint
    preprint = Preprint.load(preprint_id)
    if not preprint:
        return
    need_update = bool(preprint.SEARCH_UPDATE_FIELDS.intersection(saved_fields or {}))

    if need_update:
        preprint.update_search()

    if should_update_preprint_identifiers(preprint, saved_fields):
        update_or_create_preprint_identifiers(preprint)


def should_update_preprint_identifiers(preprint, saved_fields):
    # Only update identifier metadata iff...
    return (
        # DOI didn't just get created
        preprint and preprint.date_published and
        not (saved_fields and 'preprint_doi_created' in saved_fields) and
        # preprint isn't QA test
        preprint.should_request_identifiers
    )


def update_or_create_preprint_identifiers(preprint):
    try:
        preprint.request_identifier_update(category='doi', create=True)
    except HTTPError as err:
        sentry.log_exception(err)
        sentry.log_message(err.args[0])


def update_or_enqueue_on_preprint_updated(preprint_id, saved_fields=None):
    task = get_task_from_postcommit_queue(
        'website.preprints.tasks.on_preprint_updated',
        predicate=lambda task: task.kwargs['preprint_id'] == preprint_id
    )
    if task:
        task.kwargs['saved_fields'] = list(set(task.kwargs['saved_fields']).union(saved_fields))
    else:
        enqueue_postcommit_task(
            on_preprint_updated,
            (),
            {
                'preprint_id': preprint_id,
                'saved_fields': saved_fields
            },
            celery=True
        )


@celery_app.task(ignore_results=True, max_retries=5, default_retry_delay=CROSSREF_FAIL_RETRY_DELAY)
def mint_doi_on_crossref_fail(preprint_id):
    from osf.models import Preprint
    preprint = Preprint.load(preprint_id)
    existing_versions_without_minted_doi = Preprint.objects.filter(
        versioned_guids__guid=preprint.versioned_guids.first().guid,
        versioned_guids__version__lt=preprint.versioned_guids.first().version,
        preprint_doi_created__isnull=True
    ).exclude(id=preprint.id)
    if existing_versions_without_minted_doi:
        logger.error(
            f'There are existing preprint versions for preprint with guid {preprint._id} that are missing DOIs. Versions: '
            f'{list(existing_versions_without_minted_doi.values_list('versioned_guids__version', flat=True))}'
        )
        mint_doi_on_crossref_fail.retry(countdown=CROSSREF_FAIL_RETRY_DELAY)
    else:
        crossref_client = preprint.get_doi_client()
        if crossref_client:
            crossref_client.create_identifier(preprint, category='doi', include_relation=False)
