"""Utilities for pushing metadata to SHARE/Trove

SHARE/Trove accepts metadata records as "indexcards" in turtle format: https://www.w3.org/TR/turtle/
"""
import logging
import random

from celery.exceptions import Retry
from django.apps import apps
import requests

from framework.celery_tasks import app as celery_app
from framework.celery_tasks.handlers import enqueue_task
from framework.sentry import log_exception
from osf.metadata.osf_gathering import osf_iri
from osf.metadata.tools import pls_gather_metadata_file
from website import settings


logger = logging.getLogger(__name__)


def shtrove_ingest_url():
    return f'{settings.SHARE_URL}api/v3/ingest'


def is_qa_resource(resource):
    """
    QA puts tags and special titles on their project to stop them from appearing in the search results. This function
    check if a resource is a 'QA resource' that should be indexed.
    :param resource: should be Node/Registration/Preprint
    :return:
    """
    tags = set(resource.tags.all().values_list('name', flat=True))
    has_qa_tags = bool(set(settings.DO_NOT_INDEX_LIST['tags']).intersection(tags))

    has_qa_title = False
    _title = getattr(resource, 'title', None)
    if _title:
        has_qa_title = any((_substring in _title) for _substring in settings.DO_NOT_INDEX_LIST['titles'])

    return has_qa_tags or has_qa_title


def update_share(resource):
    if not settings.SHARE_ENABLED:
        return
    if not hasattr(resource, 'guids'):
        logger.error(f'update_share called on non-guid resource: {resource}')
        return
    _enqueue_update_share(resource)


def _enqueue_update_share(osfresource):
    _osfguid_value = osfresource.guids.values_list('_id', flat=True).first()
    if not _osfguid_value:
        logger.warning(f'update_share skipping resource that has no guids: {osfresource}')
        return
    enqueue_task(task__update_share.s(_osfguid_value))


@celery_app.task(bind=True, max_retries=4, acks_late=True)
def task__update_share(self, guid: str):
    """
    This function updates share  takes Preprints, Projects and Registrations.
    :param self:
    :param guid:
    :return:
    """
    resp = _do_update_share(guid)
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


def pls_send_trove_indexcard(osf_item):
    _iri = osf_iri(osf_item)
    if not _iri:
        raise ValueError(f'could not get iri for {osf_item}')
    _metadata_record = pls_gather_metadata_file(osf_item, 'turtle')
    return requests.post(
        shtrove_ingest_url(),
        params={
            'focus_iri': _iri,
            'record_identifier': _shtrove_record_identifier(osf_item),
        },
        headers={
            'Content-Type': _metadata_record.mediatype,
            **_shtrove_auth_headers(osf_item),
        },
        data=_metadata_record.serialized_metadata,
    )


def pls_delete_trove_indexcard(osf_item):
    return requests.delete(
        shtrove_ingest_url(),
        params={
            'record_identifier': _shtrove_record_identifier(osf_item),
        },
        headers=_shtrove_auth_headers(osf_item),
    )


def _do_update_share(osfguid: str):
    logger.debug('%s._do_update_share("%s")', __name__, osfguid)
    _guid_instance = apps.get_model('osf.Guid').load(osfguid)
    if _guid_instance is None:
        raise ValueError(f'unknown osfguid "{osfguid}"')
    _resource = _guid_instance.referent
    _response = (
        pls_delete_trove_indexcard(_resource)
        if _should_delete_indexcard(_resource)
        else pls_send_trove_indexcard(_resource)
    )
    return _response


def _shtrove_record_identifier(osf_item):
    return osf_item.guids.values_list('_id', flat=True).first()


def _shtrove_auth_headers(osf_item):
    _nonfile_item = (
        osf_item.target
        if hasattr(osf_item, 'target')
        else osf_item
    )
    _access_token = (
        _nonfile_item.provider.access_token
        if getattr(_nonfile_item, 'provider', None) and _nonfile_item.provider.access_token
        else settings.SHARE_API_TOKEN
    )
    return {'Authorization': f'Bearer {_access_token}'}


def _should_delete_indexcard(osf_item):
    if getattr(osf_item, 'is_deleted', False) or getattr(osf_item, 'deleted', None):
        return True
    # if it quacks like BaseFileNode, look at .target instead
    _containing_item = getattr(osf_item, 'target', None)
    if _containing_item:
        return _should_delete_indexcard(_containing_item)
    return (
        not _is_item_public(osf_item)
        or getattr(osf_item, 'is_spam', False)
        or is_qa_resource(osf_item)
    )


def _is_item_public(guid_referent) -> bool:
    if hasattr(guid_referent, 'verified_publishable'):
        return guid_referent.verified_publishable        # quacks like Preprint
    return getattr(guid_referent, 'is_public', False)    # quacks like AbstractNode
