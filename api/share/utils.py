"""Utilities for pushing metadata to SHARE/Trove

SHARE/Trove accepts metadata records as "indexcards" in turtle format: https://www.w3.org/TR/turtle/
"""
from http import HTTPStatus
import logging
from rdflib import Graph

from django.apps import apps
from django.db.models import Q, OuterRef, Subquery
from django.contrib.contenttypes.models import ContentType
from celery.utils.time import get_exponential_backoff_interval
import requests


from framework.celery_tasks import app as celery_app
from framework.celery_tasks.handlers import enqueue_task
from framework.encryption import ensure_bytes
from framework.sentry import log_exception
from osf.external.gravy_valet.exceptions import GVException
from osf.metadata.rdfutils import OSF
from osf.metadata.osf_gathering import (
    OsfmapPartition,
    pls_get_magic_metadata_basket,
)
from osf.metadata.serializers import get_metadata_serializer
from website import settings


logger = logging.getLogger(__name__)

# After a guid is reassigned, records that mention the object are re-sent in chunks, one chunk per task run
GUID_REASSIGN_RELATED_CHUNK_SIZE = 200
GUID_REASSIGN_RELATED_CHUNK_DELAY = 60  # seconds between chunks


def shtrove_ingest_url():
    return f'{settings.SHARE_URL}trove/ingest'


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


def update_share_after_guid_reassign(resource, old_osfid: str):
    if not settings.SHARE_ENABLED:
        return
    _enqueue_update_share(resource)
    _new_osfid = resource.guids.values_list('_id', flat=True).first()
    if _new_osfid:
        _template_cedar_ids = list(
            resource.guids.first().cedar_metadata_records.values_list('template__cedar_id', flat=True),
        )
        enqueue_task(task__delete_share_records_for_old_guid.s(old_osfid, _new_osfid, _template_cedar_ids))
        enqueue_task(task__update_share_for_related_after_guid_reassign.s(_new_osfid))


def get_related_querysets_after_guid_reassign(resource) -> list:
    from osf.models import AbstractNode, BaseFileNode, Contributor, NodeRelation, OSFUser, Preprint, PreprintContributor

    _public_nodes = AbstractNode.objects.filter(is_public=True, is_deleted=False)
    _public_preprints = Preprint.objects.filter(is_public=True, deleted__isnull=True)
    if isinstance(resource, OSFUser):
        return [
            _public_nodes.filter(
                pk__in=Contributor.objects.filter(user=resource, visible=True).values('node_id'),
            ),
            _public_preprints.filter(
                pk__in=PreprintContributor.objects.filter(user=resource, visible=True).values('preprint_id'),
            ),
        ]
    if isinstance(resource, AbstractNode):
        if not resource.is_public or resource.is_deleted:
            return []
        return [
            _public_nodes.filter(
                Q(root_id=resource.pk)  # hasRoot
                | Q(pk__in=NodeRelation.objects.filter(parent=resource).values('child_id'))  # isPartOf
                | Q(pk__in=NodeRelation.objects.filter(child=resource).values('parent_id'))  # hasPart, references
                | Q(registered_from_id=resource.pk),  # isVersionOf
            ).exclude(pk=resource.pk),
            _public_preprints.filter(node=resource),  # isSupplementedBy
            BaseFileNode.active.filter(  # isContainedBy
                target_object_id=resource.pk,
                target_content_type=ContentType.objects.get_for_model(resource),
                pk__in=apps.get_model('osf.Guid').objects.filter(
                    content_type=ContentType.objects.get_for_model(BaseFileNode),
                ).values('object_id'),
            ),
        ]
    if isinstance(resource, BaseFileNode):
        _target = resource.target
        if isinstance(_target, AbstractNode):  # contains
            return [_public_nodes.filter(pk=_target.pk)]
        if isinstance(_target, Preprint):
            return [_public_preprints.filter(pk=_target.pk)]
    return []


def _enqueue_update_share(osfresource):
    _osfguid_value = osfresource.guids.values_list('_id', flat=True).first()
    if not _osfguid_value:
        logger.warning(f'update_share skipping resource that has no guids: {osfresource}')
        return
    enqueue_task(task__update_share.s(_osfguid_value))


def retry_shtrove_request(self_celery_task, _response):
    try:
        _response.raise_for_status()
    except Exception as e:
        log_exception(e)
        if _response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            retry_after = _response.headers.get('Retry-After')
            try:
                countdown = int(retry_after)
            except (TypeError, ValueError):
                retries = getattr(self_celery_task.request, 'retries', 0)
                countdown = get_exponential_backoff_interval(
                    factor=4,
                    retries=retries,
                    maximum=2 * 60,
                    full_jitter=True,
                )
            raise self_celery_task.retry(exc=e, countdown=countdown)

        raise self_celery_task.retry(exc=e)


def cedar_record_to_turtle(referent, cedar_record):
    graph = Graph()
    iri = referent.get_semantic_iri()
    full_metadata = {
        '@id': iri,
        OSF.hasCedarRecord: cedar_record.metadata,
    }
    graph.parse(data=full_metadata, format='json-ld')

    return graph.serialize(format='turtle')


@celery_app.task(bind=True)
def share_update_cedar_metadata_record(self, referent_id, cedar_record_pk):
    from osf.models import Guid, CedarMetadataRecord

    guid = Guid.load(referent_id)
    referent = guid.referent
    cedar_record = CedarMetadataRecord.objects.filter(pk=cedar_record_pk).first()
    if not cedar_record:
        return

    serialized_data = cedar_record_to_turtle(referent, cedar_record)
    response = requests.post(
        shtrove_ingest_url(),
        params={
            'focus_iri': referent.get_semantic_iri(),
            'record_identifier': _shtrove_cedar_record_identifier(referent._id, cedar_record.template.cedar_id),
            'is_supplementary': True,
        },
        headers={
            'Content-Type': 'text/turtle; charset=utf-8',
            **_shtrove_auth_headers(referent),
        },
        data=ensure_bytes(serialized_data),
    )
    retry_shtrove_request(self, response)


@celery_app.task(bind=True)
def share_delete_cedar_metadata_record(
    self,
    cedar_referent___id,
    cedar_record___id,
    cedar_template_cedar_id,
):
    from osf.models import Guid
    referent = Guid.load(cedar_referent___id).referent
    response = requests.delete(
        shtrove_ingest_url(),
        params={
            'record_identifier': _shtrove_cedar_record_identifier(cedar_referent___id, cedar_template_cedar_id),
        },
        headers=_shtrove_auth_headers(referent),
    )
    retry_shtrove_request(self, response)


@celery_app.task(
    bind=True,
    acks_late=True,
    max_retries=4,
    retry_backoff=True,
    soft_time_limit=settings.SHARE_UPDATE_TASK_SOFT_TIME_LIMIT,
    time_limit=settings.SHARE_UPDATE_TASK_HARD_TIME_LIMIT,
)
def task__delete_share_records_for_old_guid(self, old_osfid: str, new_osfid: str, cedar_template_ids=()):
    """Delete every SHARE/trove record stored under a guid that no longer exists (see ``reassign_guid``)."""
    _resource = apps.get_model('osf.Guid').load(new_osfid).referent
    for _partition in OsfmapPartition:
        try:
            _response = pls_delete_trove_record(_resource, osfmap_partition=_partition, osfid=old_osfid)
        except GVException as e:
            log_exception(e)
            raise self.retry(exc=e)
        retry_shtrove_request(self, _response)
    for _cedar_id in cedar_template_ids:
        _response = requests.delete(
            shtrove_ingest_url(),
            params={'record_identifier': _shtrove_cedar_record_identifier(old_osfid, _cedar_id)},
            headers=_shtrove_auth_headers(_resource),
            timeout=settings.EXTERNAL_REQUEST_TIMEOUT,
        )
        retry_shtrove_request(self, _response)


@celery_app.task(bind=True, acks_late=True)
def task__update_share_for_related_after_guid_reassign(
    self,
    new_osfid: str,
    queryset_index: int = 0,
    start_id: int = 0,
    chunk_size: int = GUID_REASSIGN_RELATED_CHUNK_SIZE,
):
    """Re-send the SHARE records that mention a reassigned guid (see ``reassign_guid``).

    Each run queues one chunk of low-priority updates, then schedules itself for the next chunk, so reassigning
    the guid of a user with thousands of contributions does not flood the queue.
    """
    from osf.management.commands.recatalog_metadata import recatalog_chunk

    _osfid_instance = apps.get_model('osf.Guid').load(new_osfid)
    if _osfid_instance is None or _osfid_instance.referent is None:
        logger.warning(f'skipping related SHARE updates, unknown osfguid "{new_osfid}"')
        return
    _querysets = get_related_querysets_after_guid_reassign(_osfid_instance.referent)
    while queryset_index < len(_querysets):
        _last_id = recatalog_chunk(_querysets[queryset_index], start_id, chunk_size)
        if _last_id is not None:
            self.apply_async(
                kwargs={
                    'new_osfid': new_osfid,
                    'queryset_index': queryset_index,
                    'start_id': _last_id + 1,
                    'chunk_size': chunk_size,
                },
                countdown=GUID_REASSIGN_RELATED_CHUNK_DELAY,
            )
            return
        queryset_index += 1
        start_id = 0


def _schedule_cedar_record_updates(guid_instance):
    for cedar_record in guid_instance.cedar_metadata_records.filter(
        is_published=True,
        template__should_index_for_search=True,
    ):
        share_update_cedar_metadata_record.delay(guid_instance._id, cedar_record.pk)
    for cedar_record in guid_instance.cedar_metadata_records.filter(
        Q(is_published=False) | Q(template__should_index_for_search=False),
    ):
        share_delete_cedar_metadata_record.delay(
            cedar_record.guid._id,
            cedar_record._id,
            cedar_record.template.cedar_id,
        )


@celery_app.task(
    bind=True,
    acks_late=True,
    max_retries=4,
    retry_backoff=True,
    soft_time_limit=settings.SHARE_UPDATE_TASK_SOFT_TIME_LIMIT,
    time_limit=settings.SHARE_UPDATE_TASK_HARD_TIME_LIMIT,
)
def task__update_share(self, guid: str, is_backfill=False, osfmap_partition_name='MAIN'):
    """
    Send SHARE/trove current metadata record(s) for the osf-guid-identified object
    """
    _osfmap_partition = OsfmapPartition[osfmap_partition_name]
    _osfid_instance = apps.get_model('osf.Guid').load(guid)
    if _osfid_instance is None:
        raise ValueError(f'unknown osfguid "{guid}"')
    _resource = _osfid_instance.referent
    _is_deletion = _should_delete_indexcard(_resource)
    _resource.mark_indexing_failed()
    try:
        _response = (
            pls_delete_trove_record(_resource, osfmap_partition=_osfmap_partition)
            if _is_deletion
            else pls_send_trove_record(
                _resource,
                is_backfill=is_backfill,
                osfmap_partition=_osfmap_partition,
            )
        )
    except GVException as e:
        log_exception(e)
        raise self.retry(exc=e)

    retry_shtrove_request(self, _response)
    # success response
    if _is_deletion:
        return

    # enqueue followup task for supplementary metadata
    _next_partition = _next_osfmap_partition(_osfmap_partition)
    if _next_partition is not None:
        task__update_share.delay(
            guid,
            is_backfill=is_backfill,
            osfmap_partition_name=_next_partition.name,
        )
    else:
        _schedule_cedar_record_updates(_osfid_instance)
        _resource.mark_indexing_success()


@celery_app.task
def task__reindex_failed_or_not_indexed_resource_into_share(resource_type: str, start_id: int = 0, chunk_count: int = 200, chunk_size: int = 500):
    from osf.management.commands.recatalog_metadata import recatalog
    queryset = get_not_indexed_guids_for_resource_with_no_indexed_guid(resource_type, only_oldest_guid=False)
    # chunk count and chunk size up to discussion what will be better with Cloud Team
    recatalog(queryset, start_id, chunk_count, chunk_size)


def get_not_indexed_guids_for_resource_with_no_indexed_guid(resource_type: str, only_oldest_guid: bool = True):
    from osf.models import Guid, Registration, Preprint, Node, OSFUser, SpamStatus
    from addons.osfstorage.models import OsfStorageFile
    common_not_indexed_public_resource_extract_query = (
        Q(is_public=True) & Q(deleted__isnull=True) &
        (Q(has_been_indexed=False) | Q(has_been_indexed__isnull=True))
    )
    resource_mapper = {
        'projects': (Node, common_not_indexed_public_resource_extract_query, ('first_guid', 'date_last_indexed', 'title')),
        'preprints': (Preprint, common_not_indexed_public_resource_extract_query & Q(is_published=True), ('first_guid', 'date_last_indexed', 'title')),
        'registries': (Registration, common_not_indexed_public_resource_extract_query, ('first_guid', 'date_last_indexed', 'title')),
        'users': (OSFUser, Q(is_active=True) & Q(deleted__isnull=True) & ~Q(allow_indexing=False) & ~Q(spam_status=SpamStatus.SPAM) & (Q(has_been_indexed=False) | Q(has_been_indexed__isnull=True)), ('first_guid', 'fullname', 'date_last_indexed')),
        'files': (OsfStorageFile, Q(deleted__isnull=True), ('first_guid', 'name', 'date_last_indexed')),
    }
    resource_model, query, values_to_return = resource_mapper.get(resource_type, 'projects')
    if only_oldest_guid:
        model_content_type = ContentType.objects.get_for_model(resource_model)
        first_guid_sq = Guid.objects.filter(
            content_type=model_content_type,
            object_id=OuterRef('pk'),
        ).order_by('created').values('_id')[:1]
        return resource_model.objects.filter(query).annotate(first_guid=Subquery(first_guid_sq)).exclude(first_guid__isnull=True).values(*values_to_return)
    return resource_model.objects.filter(query)


def pls_send_trove_record(osf_item, *, is_backfill: bool, osfmap_partition: OsfmapPartition):
    try:
        _iri = osf_item.get_semantic_iri()
    except (AttributeError, ValueError):
        raise ValueError(f'could not get iri for {osf_item}')
    _basket = pls_get_magic_metadata_basket(osf_item)
    _serializer = get_metadata_serializer(
        format_key='turtle',
        basket=_basket,
        serializer_config={'osfmap_partition': osfmap_partition},
    )
    _serialized_record = _serializer.serialize()
    _queryparams = {
        'focus_iri': _iri,
        'record_identifier': _shtrove_record_identifier(osf_item, osfmap_partition),
    }
    if is_backfill:
        _queryparams['nonurgent'] = ''
    if osfmap_partition.is_supplementary:
        _queryparams['is_supplementary'] = ''
        _expiration_date = osfmap_partition.get_expiration_date(_basket)
        if _expiration_date is not None:
            _queryparams['expiration_date'] = str(_expiration_date)
    return requests.post(
        shtrove_ingest_url(),
        params=_queryparams,
        headers={
            'Content-Type': _serializer.mediatype,
            **_shtrove_auth_headers(osf_item),
        },
        data=ensure_bytes(_serialized_record),
        timeout=settings.EXTERNAL_REQUEST_TIMEOUT,
    )


def pls_delete_trove_record(osf_item, osfmap_partition: OsfmapPartition, osfid: str | None = None):
    return requests.delete(
        shtrove_ingest_url(),
        params={
            'record_identifier': _shtrove_record_identifier(osf_item, osfmap_partition, osfid=osfid),
        },
        headers=_shtrove_auth_headers(osf_item),
        timeout=settings.EXTERNAL_REQUEST_TIMEOUT,
    )


def _shtrove_record_identifier(osf_item, osfmap_partition: OsfmapPartition, osfid: str | None = None):
    _id = osfid or osf_item.guids.values_list('_id', flat=True).first()
    return (
        f'{_id}/{osfmap_partition.name}'
        if osfmap_partition.is_supplementary
        else _id
    )


def _shtrove_cedar_record_identifier(referent_osfid, template_cedar_id) -> str:
    return f'{referent_osfid}/CedarMetadataRecord:{template_cedar_id}'


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
        return not osf_item.should_update_search or _should_delete_indexcard(_containing_item)
    return (
        not _is_item_public(osf_item)
        or getattr(osf_item, 'is_spam', False)
        or is_qa_resource(osf_item)
    )


def _is_item_public(guid_referent) -> bool:
    if hasattr(guid_referent, 'verified_publishable'):
        return guid_referent.verified_publishable        # quacks like Preprint
    return getattr(guid_referent, 'is_public', False)    # quacks like AbstractNode


def _next_osfmap_partition(partition: OsfmapPartition) -> OsfmapPartition | None:
    match partition:
        case OsfmapPartition.MAIN:
            return OsfmapPartition.SUPPLEMENT
        case OsfmapPartition.SUPPLEMENT:
            return OsfmapPartition.MONTHLY_SUPPLEMENT
        case _:
            return None
