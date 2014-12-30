import os
import json
import asyncio

import aiohttp
from boto.glacier.layer2 import Layer2

from waterbutler.providers.osfstorage import settings
from waterbutler.providers.osfstorage.tasks import utils


def _get_layer2():
    return Layer2(
        aws_access_key_id=settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SECRET_KEY,
    )
layer2_proxy = utils.LazyContainer(_get_layer2)


def _get_glacier_vault():
    return layer2_proxy.get().create_vault(settings.GLACIER_VAULT)
vault_proxy = utils.LazyContainer(_get_glacier_vault)


@utils.task
def _push_file_archive(self, local_path, version_id, callback_url):
    _, name = os.path.split(local_path)
    with utils.RetryUpload(self):
        vault = vault_proxy.get()
        glacier_id = vault.upload_archive(local_path, description=name)
    metadata = {
        'vault': vault.name,
        'archive': glacier_id,
    }
    _push_archive_complete.delay(version_id, callback_url, metadata)


@utils.task
def _push_archive_complete(self, version_id, callback_url, metadata):
    with utils.RetryHook(self):
        future = aiohttp.request(
            'PUT',
            callback_url,
            data=json.dumps({
                'version_id': version_id,
                'metadata': metadata,
            }),
            headers={'Content-Type': 'application/json'},
        )
        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(future)
        if response.status != 200:
            raise Exception


def main(local_path, version_id, callback_url):
    return _push_file_archive.delay(local_path, version_id, callback_url)