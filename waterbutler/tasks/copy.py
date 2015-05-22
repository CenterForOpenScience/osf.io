import time
import logging

from waterbutler.core import utils
from waterbutler.tasks import core
from waterbutler.tasks import settings

logger = logging.getLogger(__name__)


@core.celery_task
def copy(src_bundle, dest_bundle, callback_url, auth, start_time=None, **kwargs):
    start_time = start_time or time.time()
    src_path, src_provider = src_bundle.pop('path'), utils.make_provider(**src_bundle.pop('provider'))
    dest_path, dest_provider = dest_bundle.pop('path'), utils.make_provider(**dest_bundle.pop('provider'))

    data = {
        'errors': [],
        'action': 'copy',
        'source': dict(src_bundle, **{
            'path': src_path.path,
            'name': src_path.name,
            'materialized': str(src_path),
            'provider': src_provider.NAME,
        }),
        'destination': dict(dest_bundle, **{
            'path': dest_path.path,
            'name': dest_path.name,
            'materialized': str(dest_path),
            'provider': dest_provider.NAME,
        }),
        'auth': auth['auth'],
    }

    logger.info('Starting copying {!r}, {!r} to {!r}, {!r}'.format(src_path, src_provider, dest_path, dest_provider))

    try:
        metadata, created = yield from src_provider.copy(dest_provider, src_path, dest_path, **kwargs)
    except Exception as e:
        logger.error('Copy failed with error {!r}'.format(e))
        data.update({'errors': [e.__repr__()]})
        raise  # Ensure sentry sees this
    else:
        logger.info('Copy succeeded')
        data.update({'destination': dict(src_bundle, **metadata)})
    finally:
        resp = yield from utils.send_signed_request('PUT', callback_url, dict(data, **{
            'time': time.time() + 60,
            'email': time.time() - start_time > settings.WAIT_TIMEOUT
        }))
        logger.info('Callback returned {!r}'.format(resp))

    return metadata, created
