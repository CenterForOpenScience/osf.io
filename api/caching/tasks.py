from future.moves.urllib.parse import urlparse
from django.db import connection
from django.db.models import Sum

import requests
import logging

from django.apps import apps
from api.caching.utils import storage_usage_cache
from framework.postcommit_tasks.handlers import enqueue_postcommit_task

from api.caching import settings as cache_settings
from framework.celery_tasks import app
from website import settings

logger = logging.getLogger(__name__)


def get_varnish_servers():
    #  TODO: this should get the varnish servers from HAProxy or a setting
    return settings.VARNISH_SERVERS


def get_bannable_urls(instance):
    from osf.models import Comment
    bannable_urls = []
    parsed_absolute_url = {}

    if not hasattr(instance, 'absolute_api_v2_url'):
        logger.warning('Tried to ban {}:{} but it didn\'t have a absolute_api_v2_url method'.format(instance.__class__, instance))
        return [], ''

    for host in get_varnish_servers():
        # add instance url
        varnish_parsed_url = urlparse(host)
        parsed_absolute_url = urlparse(instance.absolute_api_v2_url)
        url_string = '{scheme}://{netloc}{path}.*'.format(
            scheme=varnish_parsed_url.scheme,
            netloc=varnish_parsed_url.netloc,
            path=parsed_absolute_url.path,
        )
        bannable_urls.append(url_string)
        if isinstance(instance, Comment):
            try:
                parsed_target_url = urlparse(instance.target.referent.absolute_api_v2_url)
            except AttributeError:
                # some referents don't have an absolute_api_v2_url
                # I'm looking at you NodeWikiPage
                # Note: NodeWikiPage has been deprecated. Is this an issue with WikiPage/WikiVersion?
                pass
            else:
                url_string = '{scheme}://{netloc}{path}.*'.format(
                    scheme=varnish_parsed_url.scheme,
                    netloc=varnish_parsed_url.netloc,
                    path=parsed_target_url.path,
                )
                bannable_urls.append(url_string)

            try:
                parsed_root_target_url = urlparse(instance.root_target.referent.absolute_api_v2_url)
            except AttributeError:
                # some root_targets don't have an absolute_api_v2_url
                pass
            else:
                url_string = '{scheme}://{netloc}{path}.*'.format(
                    scheme=varnish_parsed_url.scheme,
                    netloc=varnish_parsed_url.netloc,
                    path=parsed_root_target_url.path,
                )
                bannable_urls.append(url_string)

    return bannable_urls, parsed_absolute_url.hostname


@app.task(max_retries=5, default_retry_delay=60)
def ban_url(instance):
    # TODO: Refactor; Pull url generation into postcommit_task handling so we only ban urls once per request
    timeout = 0.3  # 300ms timeout for bans
    if settings.ENABLE_VARNISH:
        bannable_urls, hostname = get_bannable_urls(instance)

        for url_to_ban in set(bannable_urls):
            try:
                response = requests.request(
                    'BAN', url_to_ban, timeout=timeout, headers=dict(
                        Host=hostname,
                    ),
                )
            except Exception as ex:
                logger.error('Banning {} failed: {}'.format(
                    url_to_ban,
                    ex.message,
                ))
            else:
                if not response.ok:
                    logger.error('Banning {} failed: {}'.format(
                        url_to_ban,
                        response.text,
                    ))
                else:
                    logger.info('Banning {} succeeded'.format(
                        url_to_ban,
                    ))


@app.task(max_retries=5, default_retry_delay=10)
def update_storage_usage_cache(target_id, target_guid, per_page=500000):
    if not settings.ENABLE_STORAGE_USAGE_CACHE:
        return
    sql = """
        SELECT count(size), sum(size) from
        (SELECT size FROM osf_basefileversionsthrough AS obfnv
        LEFT JOIN osf_basefilenode file ON obfnv.basefilenode_id = file.id
        LEFT JOIN osf_fileversion version ON obfnv.fileversion_id = version.id
        LEFT JOIN django_content_type type on file.target_content_type_id = type.id
        WHERE file.provider = 'osfstorage'
        AND type.model = 'abstractnode'
        AND file.deleted_on IS NULL
        AND file.target_object_id=%s
        ORDER BY version.id
        LIMIT %s OFFSET %s) file_page
    """
    count = per_page
    offset = 0
    storage_usage_total = 0
    with connection.cursor() as cursor:
        while count:
            cursor.execute(sql, [target_id, per_page, offset])
            result = cursor.fetchall()
            storage_usage_total += int(result[0][1]) if result[0][1] else 0
            count = int(result[0][0]) if result[0][0] else 0
            offset += count

    key = cache_settings.STORAGE_USAGE_KEY.format(target_id=target_guid)
    storage_usage_cache.set(key, storage_usage_total, settings.STORAGE_USAGE_CACHE_TIMEOUT)


def update_storage_usage(target):
    Preprint = apps.get_model('osf.preprint')

    if settings.ENABLE_STORAGE_USAGE_CACHE and not isinstance(target, Preprint) and not target.is_quickfiles:
        enqueue_postcommit_task(update_storage_usage_cache, (target.id, target._id,), {}, celery=True)

def update_storage_usage_with_size(payload):
    BaseFileNode = apps.get_model('osf.basefilenode')
    AbstractNode = apps.get_model('osf.abstractnode')

    metadata = payload.get('metadata') or payload.get('destination')

    if not metadata.get('nid'):
        return
    target_node = AbstractNode.load(metadata['nid'])

    if target_node.is_quickfiles:
        return

    action = payload['action']
    provider = metadata.get('provider', 'osfstorage')

    target_file_id = metadata['path'].replace('/', '')
    target_file_size = metadata.get('sizeInt', 0)

    if target_node.storage_limit_status is settings.StorageLimits.NOT_CALCULATED:
        return update_storage_usage(target_node)

    current_usage = target_node.storage_usage
    target_file = BaseFileNode.load(target_file_id)

    if target_file and action in ['copy', 'delete', 'move']:

        target_file_size = target_file.versions.aggregate(Sum('size'))['size__sum'] or target_file_size

    if action in ['create', 'update', 'copy'] and provider == 'osfstorage':
        current_usage += target_file_size

    elif action == 'delete' and provider == 'osfstorage':
        current_usage = max(current_usage - target_file_size, 0)

    elif action in 'move':
        source_node = AbstractNode.load(payload['source']['nid'])  # Getting the 'from' node

        source_provider = payload['source']['provider']
        if target_node == source_node and source_provider == provider:
            return  # Its not going anywhere.
        if source_provider == 'osfstorage' and not source_node.is_quickfiles:
            if source_node.storage_limit_status is settings.StorageLimits.NOT_CALCULATED:
                return update_storage_usage(source_node)

            source_node_usage = source_node.storage_usage
            source_node_usage = max(source_node_usage - target_file_size, 0)

            key = cache_settings.STORAGE_USAGE_KEY.format(target_id=source_node._id)
            storage_usage_cache.set(key, source_node_usage, settings.STORAGE_USAGE_CACHE_TIMEOUT)

        current_usage += target_file_size

        if provider != 'osfstorage':
            return  # We don't want to update the destination node if the provider isn't osfstorage
    else:
        return

    key = cache_settings.STORAGE_USAGE_KEY.format(target_id=target_node._id)
    storage_usage_cache.set(key, current_usage, settings.STORAGE_USAGE_CACHE_TIMEOUT)
