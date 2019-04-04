from future.moves.urllib.parse import urlparse

import requests
import logging

from django.apps import apps
from api.caching.utils import storage_usage_cache
from django.db import models
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
def update_storage_usage_cache(target_id):
    AbstractNode = apps.get_model('osf.AbstractNode')

    storage_usage_total = AbstractNode.objects.get(
        guids___id=target_id,
    ).files.aggregate(sum=models.Sum('versions__size'))['sum'] or 0

    key = cache_settings.STORAGE_USAGE_KEY.format(target_id=target_id)
    storage_usage_cache.set(key, storage_usage_total, cache_settings.FIVE_MIN_TIMEOUT)


def update_storage_usage(target):
    Preprint = apps.get_model('osf.preprint')

    if not isinstance(target, Preprint) and not target.is_quickfiles:
        enqueue_postcommit_task(update_storage_usage_cache, (target._id,), {}, celery=True)
