import asyncio

from waterbutler.core import utils
from waterbutler.tasks import core
from waterbutler.tasks import settings

@core.celery_task
def move(src_bundle, dest_bundle):
    src_args, src_provider = src_bundle.pop('args'), utils.make_provider(**src_bundle.pop('provider'))
    dest_args, dest_provider = dest_bundle.pop('args'), utils.make_provider(**dest_bundle.pop('provider'))

    core.ensure_event_loop().run_until_complete(
        src_provider.move(dest_provider, src_args, dest_args)
    )
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
