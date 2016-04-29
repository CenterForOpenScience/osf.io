import urlparse

import requests
import logging
from website.project.model import Comment

from website import settings

logger = logging.getLogger(__name__)


def get_varnish_servers():
    #  TODO: this should get the varnish servers from HAProxy or a setting
    return settings.VARNISH_SERVERS

def get_bannable_urls(instance):
    bannable_urls = []
    parsed_absolute_url = {}

    if not hasattr(instance, 'absolute_api_v2_url'):
        logger.warning('Tried to ban {}:{} but it didn\'t have a absolute_api_v2_url method'.format(instance.__class__, instance))
        return [], ''

    for host in get_varnish_servers():
        # add instance url
        varnish_parsed_url = urlparse.urlparse(host)
        parsed_absolute_url = urlparse.urlparse(instance.absolute_api_v2_url)
        url_string = '{scheme}://{netloc}{path}.*'.format(scheme=varnish_parsed_url.scheme,
                                                          netloc=varnish_parsed_url.netloc,
                                                          path=parsed_absolute_url.path)
        bannable_urls.append(url_string)
        if isinstance(instance, Comment):
            try:
                parsed_target_url = urlparse.urlparse(instance.target.referent.absolute_api_v2_url)
            except AttributeError:
                # some referents don't have an absolute_api_v2_url
                # I'm looking at you NodeWikiPage
                pass
            else:
                url_string = '{scheme}://{netloc}{path}.*'.format(scheme=varnish_parsed_url.scheme,
                                                                  netloc=varnish_parsed_url.netloc,
                                                                  path=parsed_target_url.path)
                bannable_urls.append(url_string)


            try:
                parsed_root_target_url = urlparse.urlparse(instance.root_target.referent.absolute_api_v2_url)
            except AttributeError:
                # some root_targets don't have an absolute_api_v2_url
                pass
            else:
                url_string = '{scheme}://{netloc}{path}.*'.format(scheme=varnish_parsed_url.scheme,
                                                              netloc=varnish_parsed_url.netloc,
                                                              path=parsed_root_target_url.path)
                bannable_urls.append(url_string)


    return bannable_urls, parsed_absolute_url.hostname


def ban_url(instance):
    # TODO: Refactor; Pull url generation into postcommit_task handling so we only ban urls once per request
    timeout = 0.3  # 300ms timeout for bans
    if settings.ENABLE_VARNISH:
        bannable_urls, hostname = get_bannable_urls(instance)

        for url_to_ban in set(bannable_urls):
            try:
                response = requests.request('BAN', url_to_ban, timeout=timeout, headers=dict(
                    Host=hostname
                ))
            except Exception as ex:
                logger.error('Banning {} failed: {}'.format(
                    url_to_ban,
                    ex.message
                ))
            else:
                if not response.ok:
                    logger.error('Banning {} failed: {}'.format(
                        url_to_ban,
                        response.text
                    ))
                else:
                    logger.info('Banning {} succeeded'.format(
                        url_to_ban
                    ))
