import os
import time

from waterbutler.core import utils
from waterbutler.tasks import core

@core.celery_task
def move(src_bundle, dest_bundle, callback_url, auth):
    src_args, src_provider = src_bundle.pop('args'), utils.make_provider(**src_bundle.pop('provider'))
    dest_args, dest_provider = dest_bundle.pop('args'), utils.make_provider(**dest_bundle.pop('provider'))

    metadata, _ = core.ensure_event_loop().run_until_complete(
        src_provider.move(dest_provider, src_args, dest_args)
    )

    if callback:
        callback(metadata)

    return (yield from utils.send_signed_request('PUT', callback_url, {
        'action': 'move',
        'source': {
            'path': self.json['source']['path'],
            'name': os.path.split(self.json['source']['path'])[1],
            'provider': source_provider.NAME,
        },
        'destination': {
            'path': data['path'],
            'name': data['name'],
            'provider': destination_provider.NAME,
        },
        'auth': auth['auth'],
        'time': time.time() + 60
    }))
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
