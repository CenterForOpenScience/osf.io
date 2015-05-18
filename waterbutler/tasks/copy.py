import time

from waterbutler.core import utils
from waterbutler.tasks import core
from waterbutler.tasks import settings


@core.celery_task
def copy(src_bundle, dest_bundle, callback_url, auth, **kwargs):
    start_time = time.time()
    src_path, src_provider = src_bundle.pop('path'), utils.make_provider(**src_bundle.pop('provider'))
    dest_path, dest_provider = dest_bundle.pop('path'), utils.make_provider(**dest_bundle.pop('provider'))

    try:
        metadata, created = yield from src_provider.copy(dest_provider, src_path, dest_path, **kwargs)
    except Exception as e:
        yield from utils.send_signed_request('PUT', callback_url, {
            'action': 'copy',
            'errors': [e.__repr__()],
            'source': {
                'path': src_path.path,
                'name': src_path.name,
                'materialized': str(src_path),
                'provider': src_provider.NAME,
            },
            'destination': {
                'path': dest_path.path,
                'name': dest_path.name,
                'materialized': str(dest_path),
                'provider': dest_provider.NAME,
            },
            'auth': auth['auth'],
            'time': time.time() + 60,
            'email': start_time - time.time() > settings.WAIT_TIMEOUT
        })
        raise  # Ensure sentry sees this

    yield from utils.send_signed_request('PUT', callback_url, {
        'action': 'copy',
        'source': {
            'path': src_path.path,
            'name': src_path.name,
            'materialized': str(src_path),
            'provider': src_provider.NAME,
        },
        'destination': metadata,
        'auth': auth['auth'],
        'time': time.time() + 60,
        'email': start_time - time.time() > settings.WAIT_TIMEOUT
    })

    return metadata, created
