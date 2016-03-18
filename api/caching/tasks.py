import urlparse

import requests
import logging

from website import settings

logger = logging.getLogger(__name__)

def get_varnish_servers():
    #  TODO: this should get the varnish servers from HAProxy or a setting
    return settings.VARNISH_SERVERS

def ban_url(url):
    timeout = 0.5  # 500ms timeout for bans
    if settings.ENABLE_VARNISH:
        parsed_url = urlparse.urlparse(url)

        for host in get_varnish_servers():
            varnish_parsed_url = urlparse.urlparse(host)
            url_to_ban = '{scheme}://{netloc}{path}.*'.format(
                scheme=varnish_parsed_url.scheme,
                netloc=varnish_parsed_url.netloc,
                path=parsed_url.path
            )
            try:
                response = requests.request('BAN', url_to_ban, timeout=timeout, headers=dict(
                    Host=parsed_url.hostname
                ))
            except Exception as ex:
                logger.error('Banning {} failed: {}'.format(
                    url,
                    ex.message
                ))
            else:
                if not response.ok:
                    logger.error('Banning {} failed: {}'.format(
                        url,
                        response.text
                    ))
