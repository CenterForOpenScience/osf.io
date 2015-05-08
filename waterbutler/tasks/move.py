import os
import time

from waterbutler.core import utils
from waterbutler.tasks import core
from waterbutler.tasks import settings


@core.celery_task
def move(src_bundle, dest_bundle, callback_url, auth, **kwargs):
    start_time = time.time()
    src_path, src_provider = src_bundle.pop('path'), utils.make_provider(**src_bundle.pop('provider'))
    dest_path, dest_provider = dest_bundle.pop('path'), utils.make_provider(**dest_bundle.pop('provider'))

    metadata, created = yield from src_provider.move(dest_provider, src_path, dest_path, **kwargs)

    yield from utils.send_signed_request('PUT', callback_url, {
        'action': 'move',
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

    # dest_provider.move()
    # stream = src_provider.download(**src_args)
    # progress = stream.ProgressStreamWriter(stream.size)
    # stream.add_writer(progress)
    # upload_task = asyncio.async(dest_provider.upload(stream, **dest_options))


# @async.coroutine
# def do_upload()

#     while not upload_task.done():
#         yield from asyncio.sleep(3)
#         progress.progress
#         # update redis
#         # sleep x seconds
