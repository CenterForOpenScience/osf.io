import os
import asyncio

from waterbutler import streams
from waterbutler import settings
from waterbutler.tasks import utils


def _get_provider():
    from waterbutler.providers import core
    return core.make_provider(
        settings.PARITY_PROVIDER_NAME,
        auth={},
        credentials=settings.PARITY_PROVIDER_CREDENTIALS,
        settings=settings.PARITY_PROVIDER_SETTINGS,
    )
provider_proxy = utils.LazyContainer(_get_provider)


@utils.task
def _parity_create_files(self, name):
    path = os.path.join(settings.FILE_PATH_COMPLETE, name)
    loop = asyncio.get_event_loop()
    with utils.RetryUpload(self):
        parity_paths = utils.create_parity_files(
            path,
            redundancy=settings.PARITY_REDUNDANCY,
        )
        futures = [asyncio.async(_upload_parity(each)) for each in parity_paths]
        loop.run_until_complete(asyncio.wait(futures))


@asyncio.coroutine
def _upload_parity(path):
    _, name = os.path.split(path)
    provider = provider_proxy.get()
    with open(path, 'rb') as file_pointer:
        stream = streams.FileStreamReader(file_pointer)
        yield from provider.upload(stream, path=name)
    # os.remove(path)


def main(name):
    return _parity_create_files.delay(name)
