import os
import json
import uuid
import shutil
import asyncio
import hashlib

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


import time
import logging
logger = logging.getLogger(__name__)


QUERY_METHODS = ('GET', 'DELETE')


class OSFPath(utils.WaterButlerPath):
    def __init__(self, path):
        super().__init__(path, prefix=True, suffix=True)


class OSFStorageProvider(provider.BaseProvider):
    __version__ = '0.0.1'

    def __init__(self, auth, credentials, settings):
        super().__init__(auth, credentials, settings)
        self.callback = settings.get('callback')
        self.metadata_url = settings.get('metadata')
        self.provider_name = settings['storage'].get('provider')
        self.parity_credentials = credentials.get('parity')
        self.parity_settings = settings.get('parity')
        self.archive_credentials = credentials.get('archive')
        self.archive_settings = settings.get('archive')

    def make_provider(self, settings):
        """Requests on different files may need to use different providers,
        instances, e.g. when different files lives in different containers
        within a provider. This helper creates a single-use provider instance
        that optionally overrides the settings.

        :param dict settings: Overridden settings
        """
        return utils.make_provider(
            self.provider_name,
            self.auth,
            self.credentials['storage'],
            self.settings['storage'],
        )

    @asyncio.coroutine
    def make_signed_request(self, method, url, data=None, params=None, ttl=100, **kwargs):
        signer = signing.Signer(settings.HMAC_SECRET, settings.HMAC_ALGORITHM)
        if method.upper() in QUERY_METHODS:
            signed = signing.sign_data(signer, params, ttl=ttl)
            params = signed
        else:
            signed = signing.sign_data(signer, json.loads(data), ttl=ttl)
            data = json.dumps(signed)
        return (yield from self.make_request(method, url, data=data, params=params, **kwargs))

    @asyncio.coroutine
    def download(self, **kwargs):
        kwargs['path'] = OSFPath(kwargs['path']).path[1:]

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
        data['data']['path'] = '/' + data['data']['path']
        return (yield from provider.download(**data['data']))

    @asyncio.coroutine
    def upload(self, stream, path, **kwargs):
        self._create_paths()

        pending_name = str(uuid.uuid4())
        pending_path = os.path.join(settings.FILE_PATH_PENDING, pending_name)

        pending_name = OSFPath('/' + pending_name).path

        stream.add_writer('md5', streams.HashStreamWriter(hashlib.md5))
        stream.add_writer('sha1', streams.HashStreamWriter(hashlib.sha1))
        stream.add_writer('sha256', streams.HashStreamWriter(hashlib.sha256))

        begin = time.time()
        with open(pending_path, 'wb') as file_pointer:
            stream.add_writer('file', file_pointer)
            provider = self.make_provider(self.settings)
            yield from provider.upload(stream, pending_name, **kwargs)
        logger.info('[{}] ({}) PROVIDER.UPLOAD({})'.format(
            time.time() - begin,
            self.__class__.__name__,
            pending_path,
        ))

        complete_name = stream.writers['sha256'].hexdigest
        complete_path = os.path.join(settings.FILE_PATH_COMPLETE, complete_name)

        complete_name = OSFPath('/' + complete_name).path

        begin = time.time()
        try:
            metadata = yield from provider.metadata(complete_name)
        except exceptions.ProviderError:
            metadata = yield from provider.move(
                provider,
                {'path': pending_name},
                {'path': complete_name},
            )
        else:
            yield from provider.delete(pending_name)
        logger.info('[{}] ({}) PROVIDER.MOVE({}, {})'.format(
            time.time() - begin,
            self.__class__.__name__,
            pending_path,
            complete_path,
        ))

        # Due to cross volume movement in unix we leverage shutil.move which properly handles this case.
        # http://bytes.com/topic/python/answers/41652-errno-18-invalid-cross-device-link-using-os-rename#post157964
        begin = time.time()
        shutil.move(pending_path, complete_path)
        logger.info('[{}] ({}) SHUTIL.MOVE({}, {})'.format(
            time.time() - begin,
            self.__class__.__name__,
            pending_path,
            complete_path,
        ))

        begin = time.time()
        response = yield from self.make_signed_request(
            'POST',
            self.callback,
            data=json.dumps({
                'auth': self.auth,
                'settings': self.settings['storage'],
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
        logger.info('[{}] ({}) MAKE_SIGNED_REQUEST(POST, {})'.format(
            time.time() - begin,
            self.__class__.__name__,
            self.callback,
        ))

        created = response.status == 201
        data = yield from response.json()

        begin = time.time()
        if settings.RUN_TASKS:
            version_id = data['version_id']
            parity.main(
                complete_path,
                self.parity_credentials,
                self.parity_settings,
            )
            backup.main(
                complete_path,
                version_id,
                self.callback,
                self.archive_credentials,
                self.archive_settings,
            )
        logger.info('[{}] ({}) RUN_TASKS'.format(
            time.time() - begin,
            self.__class__.__name__,
        ))

        _, name = os.path.split(path)

        metadata.update({
            'name': name,
            'path': path,
            'downloads': data['downloads']
        })

        return OsfStorageFileMetadata(metadata).serialized(), created

    @asyncio.coroutine
    def delete(self, **kwargs):
        kwargs['auth'] = self.auth
        kwargs['path'] = OSFPath(kwargs['path']).path[1:]

        yield from self.make_signed_request(
            'DELETE',
            self.callback,
            params=kwargs,
            expects=(200, )
        )

    @asyncio.coroutine
    def metadata(self, **kwargs):
        if kwargs['path'].startswith('/'):
            kwargs['path'] = kwargs['path'][1:]

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

    def _create_paths(self):
        try:
            os.mkdir(settings.FILE_PATH_PENDING)
        except FileExistsError:
            pass

        try:
            os.mkdir(settings.FILE_PATH_COMPLETE)
        except FileExistsError:
            pass

        return True
