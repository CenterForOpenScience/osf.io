import os
import asyncio

from waterbutler import exceptions
from waterbutler.providers import core


TEMP_URL_SECS = 100


def ensure_connection(func):
    def wrapped(self, *args, **kwargs):
        yield from self._ensure_connection()
        return func(self, *args, **kwargs)


@core.register_provider('cloudfiles')
class CloudFilesProvider(core.BaseProvider):
    """Provider for Rackspace CloudFiles
    """

    def __init__(self, auth, identity):
        super().__init__(auth, identity)
        self.container = self.identity['container']
        self.region = self.identity['region']
        self.token = self.identity['token']

    def extract_endpoint(self, data):
        for service in reversed(data['access']['serviceCatalog']):
            if service['name'] == 'cloudFiles':
                for region in service['endpoints']:
                    if region['region'] == self.region:
                        return region['publicURL']

    @asyncio.coroutine
    def _ensure_connection(self):
        if not self.token or not self.endpoint:
            data = yield from self.get_token()
            self.token = data['access']['token']['id']
            self.endpoint = self.extract_endpoint(data)

    @asyncio.coroutine
    def get_token(self):
        resp = yield from self.make_request(
            'POST',
            'https://identity.api.rackspacecloud.com/v2.0/tokens',
            data={
               'auth': {
                  'RAX-KSKEY:apiKeyCredentials': {
                     'username': self.identity['username'],
                     'apiKey': self.identity['token'],
                  }
               }
            },
            headers={
                'Content-Type': 'application/json',
            }
        )
        data = yield from resp.json()
        return data

    def build_url(self):
        pass

    def build_hmac_url(self, url, method='GET', seconds=60):
        method = method.upper()
        base_url, object_path = url.split('/v1/')
        object_path = '/v1/' + object_path
        seconds = int(seconds)
        expires = int(time() + seconds)
        hmac_body = '%s\n%s\n%s' % (method, expires, object_path)
        sig = hmac.new(key, hmac_body, sha1).hexdigest()

        url = furl.furl(urlparse.urljoin(self.endpoint, self.container))
        url = urlparse.urljoin(self.endpoint, self.container)
        url += '?' + urllib.urlencode({'temp_url_sig': sig, 'expires': expires})
        return url

    @core.expects(200)
    @asyncio.coroutine
    def download(self, path, accept_url=False, **kwargs):
        """Returns a ResponseWrapper (Stream) for the specified path
        raises FileNotFoundError if the status from S3 is not 200

        :param str path: Path to the key you want to download
        :param dict **kwargs: Additional arguments that are ignored
        :rtype ResponseWrapper:
        :raises: waterbutler.FileNotFoundError
        """
        url = build_url('...')
        if accept_url:
            return url
        resp = yield from self.make_request('GET', url)
        return core.ResponseWrapper(resp)

    @core.expects(200, 201)
    @asyncio.coroutine
    def upload(self, obj, path, **kwargs):
        """Uploads the given stream to S3
        :param ResponseWrapper obj: The stream to put to S3
        :param str path: The full path of the key to upload to/into
        :rtype ResponseWrapper:
        """
        key = self.bucket.new_key(path)
        url = key.generate_url(TEMP_URL_SECS, 'PUT')
        resp = yield from self.make_request(
            'PUT', url,
            data=obj.content,
            headers={'Content-Length': obj.size},
        )

        return core.ResponseWrapper(resp)

    @core.expects(200, 204)
    @asyncio.coroutine
    def delete(self, path, **kwargs):
        """Deletes the key at the specified path
        :param str path: The path of the key to delete
        :rtype ResponseWrapper:
        """
        key = self.bucket.new_key(path)
        url = key.generate_url(TEMP_URL_SECS, 'DELETE')
        resp = yield from self.make_request('DELETE', url)

        return core.ResponseWrapper(resp)

    @asyncio.coroutine
    def metadata(self, path, **kwargs):
        """Get Metadata about the requested file or folder
        :param str path: The path to a key or folder
        :rtype dict:
        :rtype list:
        """
        url = self.bucket.generate_url(TEMP_URL_SECS, 'GET')
        resp = yield from self.make_request('GET', url, params={'prefix': path, 'delimiter': '/'})

        if resp.status == 404:
            raise exceptions.FileNotFoundError(path)

        content = yield from resp.read_and_close()
        obj = objectify.fromstring(content)

        files = [
            self.key_to_dict(k)
            for k in getattr(obj, 'Contents', [])
        ]

        folders = [
            self.prefix_to_dict(p)
            for p in getattr(obj, 'CommonPrefixes', [])
        ]

        if len(folders) == 0 and len(files) == 1:
            return files[0]

        return files + folders

    def key_to_dict(self, key, children=[]):
        return {
            'content': children,
            'provider': 's3',
            'kind': 'file',
            'name': os.path.split(key.Key.text)[1],
            'size': key.Size.text,
            'path': key.Key.text,
            'modified': key.LastModified.text,
            'extra': {
                'md5': key.ETag.text.replace('"', ''),
            },
        }

    def prefix_to_dict(self, prefix, children=[]):
        return {
            'contents': children,
            'provider': 's3',
            'kind': 'folder',
            'name': getname(prefix.Prefix.text),
            'path': prefix.Prefix.text,
            'modified': None,
            'size': None,
            'extra': {},
        }
