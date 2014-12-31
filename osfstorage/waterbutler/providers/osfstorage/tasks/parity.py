import os
import asyncio

from stevedore import driver

from waterbutler.core import streams

from waterbutler.providers.osfstorage import settings
from waterbutler.providers.osfstorage.tasks import utils


def _get_provider():
    manager = driver.DriverManager(
        namespace='waterbutler.providers',
        name=settings.PARITY_PROVIDER_NAME,
        invoke_on_load=True,
        invoke_args=(
            {},
            settings.PARITY_PROVIDER_CREDENTIALS,
            settings.PARITY_PROVIDER_SETTINGS,
        ),
    )
    return manager.driver
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
