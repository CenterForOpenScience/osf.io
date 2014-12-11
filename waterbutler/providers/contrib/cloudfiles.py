import os
import hmac
import json
import time
import asyncio
import hashlib
import functools

import furl

from waterbutler import exceptions
from waterbutler.providers import core


TEMP_URL_SECS = 100


def ensure_connection(func):
    """Runs ``_ensure_connection`` before continuing to the method
    """
    @functools.wraps(func)
    @asyncio.coroutine
    def wrapped(self, *args, **kwargs):
        yield from self._ensure_connection()
        return (yield from func(self, *args, **kwargs))
    return wrapped


def format_metadata(data):
    if data.get('subdir'):
        return {
            'name': data['subdir'],
            'path': data['subdir']
        }
    else:
        return {
            'name': os.path.split(data['name'])[1],
            'path': data['name'],
            'size': data['bytes']
        }


@core.register_provider('cloudfiles')
class CloudFilesProvider(core.BaseProvider):
    """Provider for Rackspace CloudFiles
    """

    def __init__(self, auth, identity):
        super().__init__(auth, identity)
        self.token = None
        self.endpoint = None
        self.temp_url_key = None
        self.region = self.identity['region']
        self.og_token = self.identity['token']
        self.username = self.identity['username']
        self.container = self.identity['container']

    @asyncio.coroutine
    def get_token(self):
        """Fetchs an access token from cloudfiles for actual api requests
        Returns the entire json response from the tokens endpoint
        Notably containing our token and proper endpoint to send requests to
        :rtype dict:
        """
        resp = yield from self.make_request(
            'POST',
            'https://identity.api.rackspacecloud.com/v2.0/tokens',
            data=json.dumps({
                'auth': {
                    'RAX-KSKEY:apiKeyCredentials': {
                        'username': self.username,
                        'apiKey': self.og_token,
                    }
                }
            }),
            headers={
                'Content-Type': 'application/json',
            }
        )
        data = yield from resp.json()
        return data

    @asyncio.coroutine
    def _ensure_connection(self):
        """Defines token, endpoint and temp_url_key if they are not already defined
        :raises ProviderError: If no temp url key is available
        """
        # Must have a temp url key for download and upload
        # Currently You must have one for everything however
        if not self.token or not self.endpoint or not self.temp_url_key:
            data = yield from self.get_token()
            self.token = data['access']['token']['id']
            self.endpoint = self.extract_endpoint(data)
            resp = yield from self.make_request('HEAD', self.endpoint)
            try:
                self.temp_url_key = resp.headers['X-Account-Meta-Temp-URL-Key'].encode()
            except KeyError:
                raise exceptions.ProviderError('Not temp url key is available', code=503)

    @property
    def default_headers(self):
        return {
            'X-Auth-Token': self.token,
            'Accept': 'application/json',
        }

    def extract_endpoint(self, data):
        """Pulls the proper cloudfiles url from the return of tokens
        Very optimized.
        :param dict data: The json response from the token endpoint
        :rtype str:
        """
        for service in reversed(data['access']['serviceCatalog']):
            if service['name'] == 'cloudFiles':
                for region in service['endpoints']:
                    if region['region'] == self.region:
                        return region['publicURL']

    def build_url(self, obj):
        """Build the url for the specified object
        :param str obj: The object in question
        :rtype str:
        """
        url = furl.furl(self.endpoint)
        url.path.add(self.container)
        url.path.add(obj)
        return url.url

    def generate_url(self, obj, method='GET', seconds=60):
        """Build and sign a temp url for the specified object
        :param str obj: The requested object's path
        :param str method: The HTTP method used to access the returned url
        :param int seconds: Time for the url to live
        :rtype str:
        """
        method = method.upper()
        expires = str(int(time.time() + seconds))
        url = furl.furl(self.build_url(obj))

        body = '\n'.join([method, expires, str(url.path)]).encode()
        signature = hmac.new(self.temp_url_key, body, hashlib.sha1).hexdigest()

        url.args.update({
            'temp_url_sig': signature,
            'temp_url_expires': expires,
        })
        return url.url

    @core.expects(200)
    @ensure_connection
    def download(self, path, accept_url=False, **kwargs):
        """Returns a ResponseWrapper (Stream) for the specified path
        :param str path: Path to the object you want to download
        :param dict **kwargs: Additional arguments that are ignored
        :rtype str:
        :rtype ResponseWrapper:
        :raises: waterbutler.FileNotFoundError
        """
        url = self.generate_url(path)

        if accept_url:
            return url

        resp = yield from self.make_request('GET', url)
        return core.ResponseWrapper(resp)

    @core.expects(200, 201)
    @ensure_connection
    def upload(self, obj, path, **kwargs):
        """Uploads the given stream to S3
        :param ResponseWrapper obj: The stream to put to Cloudfiles
        :param str path: The full path of the object to upload to/into
        :rtype ResponseWrapper:
        """
        url = self.generate_url(path, 'PUT')

        resp = yield from self.make_request(
            'PUT', url,
            data=obj.content,
            headers={'Content-Length': obj.size},
        )

        return core.ResponseWrapper(resp)

    @core.expects(204)
    @ensure_connection
    def delete(self, path, **kwargs):
        """Deletes the key at the specified path
        :param str path: The path of the key to delete
        :rtype ResponseWrapper:
        """
        resp = yield from self.make_request('DELETE', self.build_url(path))

        return core.ResponseWrapper(resp)

    @ensure_connection
    def metadata(self, path, **kwargs):
        """Get Metadata about the requested file or folder
        :param str path: The path to a key or folder
        :rtype dict:
        :rtype list:
        """
        url = furl.furl(self.build_url(''))
        url.args.update({'prefix': path, 'delimiter': '/'})
        resp = yield from self.make_request('GET', url.url)

        if resp.status == 404:
            raise exceptions.FileNotFoundError(path)
        if resp.status == 204:
            return []  # TODO Correct value?

        content = yield from resp.json()

        # TODO process metadata

        return [
            format_metadata(chunk)
            for chunk in content
        ]
