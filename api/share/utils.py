"""Utilities for pushing metadata to SHARE/Trove

SHARE/Trove accepts metadata records as "indexcards" in turtle format: https://www.w3.org/TR/turtle/
"""
import logging
import random

from celery.exceptions import Retry
from django.apps import apps

from framework.celery_tasks import app as celery_app
from framework.celery_tasks.handlers import enqueue_task
from framework.sentry import log_exception
from osf.metadata.tools import pls_send_trove_indexcard, pls_delete_trove_indexcard
from website import settings


logger = logging.getLogger(__name__)


def is_qa_resource(resource):
    """
    QA puts tags and special titles on their project to stop them from appearing in the search results. This function
    check if a resource is a 'QA resource' that should be indexed.
    :param resource: should be Node/Registration/Preprint
    :return:
    """
    tags = set(resource.tags.all().values_list('name', flat=True))
    has_qa_tags = bool(set(settings.DO_NOT_INDEX_LIST['tags']).intersection(tags))

    has_qa_title = any(substring in resource.title for substring in settings.DO_NOT_INDEX_LIST['titles'])

    return has_qa_tags or has_qa_title


def update_share(resource):
    if not settings.SHARE_ENABLED:
        return
    if not hasattr(resource, 'guids'):
        logger.error(f'update_share called on non-guid resource: {resource}')
        return
    _osfguid_value = resource.guids.values_list('_id', flat=True).first()
    if not _osfguid_value:
        logger.warning(f'update_share skipping resource that has no guids: {resource}')
        return
    enqueue_task(task__update_share.s(_osfguid_value))


@celery_app.task(bind=True, max_retries=4, acks_late=True)
def task__update_share(self, guid: str, **kwargs):
    """
    This function updates share  takes Preprints, Projects and Registrations.
    :param self:
    :param guid:
    :return:
    """
    _guid_instance = apps.get_model('osf.Guid').load(guid)
    if _guid_instance is None:
        raise ValueError(f'unknown osfguid "{guid}"')
    resource = _guid_instance.referent
    resp = (
        pls_delete_trove_indexcard(resource)
        if _should_delete_indexcard(resource)
        else pls_send_trove_indexcard(resource)
    )
    try:
        resp.raise_for_status()
    except Exception as e:
        if self.request.retries == self.max_retries:
            log_exception()
        elif resp.status_code >= 500 and settings.USE_CELERY:
            try:
                self.retry(
                    exc=e,
                    countdown=(random.random() + 1) * min(60 + settings.CELERY_RETRY_BACKOFF_BASE ** self.request.retries, 60 * 10),
                )
            except Retry:  # Retry is only raise after > 5 retries
                log_exception()
        else:
            log_exception()

    return resp


def _should_delete_indexcard(osf_item):
    # if it quacks like BaseFileNode, look at .target instead
    _possibly_private_item = getattr(osf_item, 'target', None) or osf_item
    return (
        not _is_item_public(_possibly_private_item)
        or getattr(_possibly_private_item, 'is_spam', False)
        or is_qa_resource(_possibly_private_item)
    )


def _is_item_public(guid_referent) -> bool:
    if hasattr(guid_referent, 'verified_publishable'):
        return guid_referent.verified_publishable        # quacks like Preprint
    return getattr(guid_referent, 'is_public', False)    # quacks like AbstractNode
