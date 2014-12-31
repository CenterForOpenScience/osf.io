import os
import json
import time
import uuid
import asyncio
import hashlib

from stevedore import driver

from waterbutler.core import utils
from waterbutler.core import signing
from waterbutler.core import streams
from waterbutler.core import provider
from waterbutler.core import exceptions

from waterbutler.providers.osfstorage import settings
from waterbutler.providers.osfstorage.tasks import backup
from waterbutler.providers.osfstorage.tasks import parity
from waterbutler.providers.osfstorage.metadata import OsfStorageFileMetadata
from waterbutler.providers.osfstorage.metadata import OsfStorageFolderMetadata


signer = signing.Signer(settings.HMAC_SECRET, settings.HMAC_ALGORITHM)

class OSFPath(utils.WaterButlerPath):

    def __init__(self, path):
        super().__init__('/' + path, prefix=True, suffix=True)

class OSFStorageProvider(provider.BaseProvider):
    __version__ = '0.0.1'

    def __init__(self, auth, credentials, settings):
        super().__init__(auth, credentials, settings)
        self.callback = settings.pop('callback')
        self.metadata_url = settings.pop('metadata')
        self.provider_name = settings.pop('provider')

    def make_provider(self, settings):
        """Requests on different files may need to use different providers,
        instances, e.g. when different files lives in different containers
        within a provider. This helper creates a single-use provider instance
        that optionally overrides the settings.

        :param dict settings: Overridden settings
        """
        manager = driver.DriverManager(
            namespace='waterbutler.providers',
            name=self.provider_name,
            invoke_on_load=True,
            invoke_args=(
                self.auth,
                self.credentials,
                settings,
            ),
        )
        return manager.driver

    @asyncio.coroutine
    def make_signed_request(self, method, url, data=None, params=None, ttl=100, **kwargs):
        exp_time = int(time.time() + ttl)

        if method in ('GET', 'DELETE'):
            params['time'] = exp_time
            payload, signature = signer.sign_payload(params)
            params = {
                'payload': payload.decode(),
                'signature': signature
            }
        else:
            data = json.loads(data)
            data['time'] = exp_time
            payload, signature = signer.sign_payload(data)
            data = json.dumps({
                'payload': payload.decode(),
                'signature': signature
            })

        return (yield from self.make_request(method, url, data=data, params=params, **kwargs))

    @asyncio.coroutine
    def download(self, **kwargs):
        # osf storage metadata will return a virtual path within the provider
        resp = yield from self.make_signed_request(
            'GET',
            self.callback,
            params=kwargs,
            expects=(200, ),
            throws=exceptions.DownloadError,
        )

        data = yield from resp.json()
        provider = self.make_provider(data['settings'])
        data['data']['path'] = OSFPath(data['data']['path']).path

        return (yield from provider.download(**data['data']))

    @asyncio.coroutine
    def upload(self, stream, path, **kwargs):
        pending_name = str(uuid.uuid4())
        pending_path = os.path.join(settings.FILE_PATH_PENDING, pending_name)

        pending_name = OSFPath(pending_name).path

        stream.add_writer('md5', streams.HashStreamWriter(hashlib.md5))
        stream.add_writer('sha1', streams.HashStreamWriter(hashlib.sha1))
        stream.add_writer('sha256', streams.HashStreamWriter(hashlib.sha256))

        with open(pending_path, 'wb') as file_pointer:
            stream.add_writer('file', file_pointer)
            provider = self.make_provider(self.settings)
            yield from provider.upload(stream, pending_name, **kwargs)

        complete_name = stream.writers['sha256'].hexdigest
        complete_path = os.path.join(settings.FILE_PATH_COMPLETE, complete_name)

        complete_name = OSFPath(complete_name).path

        metadata = yield from provider.move(
            provider,
            {'path': pending_name},
            {'path': complete_name},
        )

        os.rename(pending_path, complete_path)

        response = yield from self.make_signed_request(
            'POST',
            self.callback,
            data=json.dumps({
                'auth': self.auth,
                'settings': self.settings,
                'metadata': metadata,
                'hashes': {
                    'md5': stream.writers['md5'].hexdigest,
                    'sha1': stream.writers['sha1'].hexdigest,
                    'sha256': stream.writers['sha256'].hexdigest,
                },
                'worker': {
                    'host': os.uname()[1],
                    # TODO: Include additional information
                    'address': None,
                    'version': self.__version__,
                },
                'path': path,
            }),
            headers={'Content-Type': 'application/json'},
        )

        created = response.status == 201
        data = yield from response.json()

        if settings.RUN_PARITY:
            version_id = data['version_id']
            parity.main(
                complete_path,
            )
            backup.main(
                complete_path,
                version_id,
                self.callback,
            )

        path, name = os.path.split(path)

        metadata.update({
            'name': name,
            'path': path
        })

        return OsfStorageFileMetadata(metadata).serialized(), created

    @asyncio.coroutine
    def delete(self, **kwargs):
        kwargs['auth'] = self.auth
        yield from self.make_signed_request(
            'DELETE',
            self.callback,
            params=kwargs,
            expects=(200, )
        )

    @asyncio.coroutine
    def metadata(self, **kwargs):
        if kwargs['path'] == '/':
            kwargs['path'] = ''

        resp = yield from self.make_signed_request(
            'GET',
            self.metadata_url,
            params=kwargs,
            expects=(200, )
        )

        ret = []
        for item in (yield from resp.json()):
            if item['kind'] == 'folder':
                ret.append(OsfStorageFolderMetadata(item).serialized())
            else:
                ret.append(OsfStorageFileMetadata(item).serialized())

        return ret
