import os
import asyncio

from waterbutler.core import streams
from waterbutler.core.utils import async_retry
from waterbutler.core.utils import make_provider

from waterbutler.providers.osfstorage.tasks import utils
from waterbutler.providers.osfstorage import settings as osf_settings


@utils.task
def _parity_create_files(self, name, credentials, settings):
    path = os.path.join(osf_settings.FILE_PATH_COMPLETE, name)
    loop = asyncio.get_event_loop()
    with utils.RetryUpload(self):
        parity_paths = utils.create_parity_files(
            path,
            redundancy=osf_settings.PARITY_REDUNDANCY,
        )
        if not parity_paths:
            #create_parity_files will return [] for empty files
            return
        futures = [asyncio.async(_upload_parity(each, credentials, settings)) for each in parity_paths]
        results, _ = loop.run_until_complete(asyncio.wait(futures, return_when=asyncio.FIRST_EXCEPTION))
        # Errors are not raised in `wait`; explicitly check results for errors
        # and raise if any found
        for each in results:
            error = each.exception()
            if error:
                raise error


@asyncio.coroutine
def _upload_parity(path, credentials, settings):
    _, name = os.path.split(path)
    provider_name = settings.get('provider')
    provider = make_provider(provider_name, {}, credentials, settings)
    with open(path, 'rb') as file_pointer:
        stream = streams.FileStreamReader(file_pointer)
        yield from provider.upload(
            stream,
            (yield from provider.validate_path('/' + name))
        )


@async_retry(retries=5, backoff=5)
def main(name, credentials, settings):
    return _parity_create_files.delay(name, credentials, settings)
