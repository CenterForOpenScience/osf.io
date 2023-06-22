"""Utilities for pushing metadata to SHARE/Trove

SHARE/Trove accepts metadata records as "indexcards" in turtle format: https://www.w3.org/TR/turtle/
"""
from django.apps import apps
import random
import requests
from framework.celery_tasks import app as celery_app
from framework.sentry import log_exception

from website import settings
from celery.exceptions import Retry
from osf.metadata.tools import pls_update_trove_indexcard, pls_delete_trove_indexcard

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
    if _should_delete_indexcard(resource):
        resp = pls_delete_trove_indexcard(resource)
    else:
        resp = pls_update_trove_indexcard(resource)
    status_code = resp.status_code
    try:
        resp.raise_for_status()
    except requests.HTTPError:
        if status_code >= 500:
            async_update_resource_share.delay(resource._id)
        else:
            log_exception()


@celery_app.task(bind=True, max_retries=4, acks_late=True)
def async_update_resource_share(self, guid, **kwargs):
    """
    This function updates share  takes Preprints, Projects and Registrations.
    :param self:
    :param guid:
    :return:
    """
    resource = apps.get_model('osf.Guid').load(guid).referent
    resp = pls_update_trove_indexcard(resource)
    try:
        resp.raise_for_status()
    except Exception as e:
        if self.request.retries == self.max_retries:
            log_exception()
        elif resp.status_code >= 500:
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
    return (
        not _is_item_public(osf_item)
        or getattr(osf_item, 'is_spam', False)
        or is_qa_resource(osf_item)
    )


def _is_item_public(guid_referent) -> bool:
    # if it quacks like BaseFileNode, look at .target instead
    _maybe_public = getattr(guid_referent, 'target', None) or guid_referent
    if hasattr(_maybe_public, 'verified_publishable'):
        return _maybe_public.verified_publishable        # quacks like Preprint
    return getattr(_maybe_public, 'is_public', None)     # quacks like AbstractNode
