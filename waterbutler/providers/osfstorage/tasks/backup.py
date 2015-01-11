import os
import http
import json
import asyncio

import aiohttp
from boto.glacier.layer2 import Layer2

from waterbutler.core import signing
from waterbutler.providers.osfstorage import settings
from waterbutler.providers.osfstorage.tasks import utils


def get_vault(credentials, settings):
    layer2 = Layer2(
        aws_access_key_id=credentials['access_key'],
        aws_secret_access_key=credentials['secret_key'],
    )
    return layer2.get_vault(settings['vault'])


@utils.task
def _push_file_archive(self, local_path, version_id, callback_url,
                       credentials, settings):
    _, name = os.path.split(local_path)
    with utils.RetryUpload(self):
        vault = get_vault(credentials, settings)
        glacier_id = vault.upload_archive(local_path, description=name)
    metadata = {
        'vault': vault.name,
        'archive': glacier_id,
    }
    _push_archive_complete.delay(version_id, callback_url, metadata)


@utils.task
def _push_archive_complete(self, version_id, callback_url, metadata):
    signer = signing.Signer(settings.HMAC_SECRET, settings.HMAC_ALGORITHM)
    with utils.RetryHook(self):
        data = signing.sign_data(
            signer,
            {
                'version_id': version_id,
                'metadata': metadata,
            },
        )
        future = aiohttp.request(
            'PUT',
            callback_url,
            data=json.dumps(data),
            headers={'Content-Type': 'application/json'},
        )
        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(future)
        if response.status != http.client.OK:
            raise Exception


def main(local_path, version_id, callback_url, credentials, settings):
    return _push_file_archive.delay(local_path, version_id, callback_url, credentials, settings)
