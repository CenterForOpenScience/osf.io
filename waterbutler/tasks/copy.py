import os
import time

from waterbutler.core import utils
from waterbutler.tasks import core


@core.celery_task
def copy(src_bundle, dest_bundle, callback_url, auth):
    src_args, src_provider = src_bundle.pop('args'), utils.make_provider(**src_bundle.pop('provider'))
    dest_args, dest_provider = dest_bundle.pop('args'), utils.make_provider(**dest_bundle.pop('provider'))

    metadata, _ = yield from src_provider.copy(dest_provider, src_args, dest_args)

    return (yield from utils.send_signed_request('PUT', callback_url, {
        'action': 'copy',
        'source': {
            'path': src_args['path'],
            'name': os.path.split(src_args['path'])[1],
            'provider': src_provider.NAME,
        },
        'destination': {
            'path': metadata['path'],
            'name': metadata['name'],
            'provider': dest_provider.NAME,
            'fullPath': metadata['fullPath'],
        },
        'auth': auth['auth'],
        'time': time.time() + 60
    }))
