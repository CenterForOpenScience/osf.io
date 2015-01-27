import os
import http
import json
import asyncio

import aiohttp
import oauthlib.oauth1

from waterbutler.core import utils
from waterbutler.core import provider
from waterbutler.core import exceptions

from waterbutler.providers.figshare import metadata
from waterbutler.providers.figshare import utils as figshare_utils


def padded_parts(path, count):
    parts = path.strip('/').split('/')
    if len(parts) > count:
        raise ValueError
    padding = [None] * (count - len(parts))
    return parts + padding


class FigsharePath(utils.WaterButlerPath):

    def _validate_path(self, path):
        """Validates a WaterButler specific path, e.g. /folder/file.txt, /folder/
        :param str path: WaterButler path
        """
        if path == '':
            return
        if not path.startswith('/'):
            raise ValueError('Invalid path \'{}\' specified'.format(path))
        if '//' in path:
            raise ValueError('Invalid path \'{}\' specified'.format(path))
        # Do not allow path manipulation via shortcuts, e.g. '..'
        absolute_path = os.path.abspath(path)
        if not path == '/' and path.endswith('/'):
            absolute_path += '/'
        if not path == absolute_path:
            raise ValueError('Invalid path \'{}\' specified'.format(absolute_path))


class FigshareProjectPath(FigsharePath):

    def __init__(self, path, *args, **kwargs):
        super().__init__(path, *args, **kwargs)
        (self.article_id, self.file_id) = padded_parts(path, 2)

    @property
    def child(self):
        try:
            path = '/{0}/'.format(os.path.join(*self.parts[2:]))
        except TypeError:
            path = '/' if self.is_dir else ''
        return self.__class__(path, prefix=self._prefix, suffix=self._suffix)


class FigshareArticlePath(FigsharePath):

    def __init__(self, path, *args, **kwargs):
        super().__init__(path, *args, **kwargs)
        (self.file_id, ) = padded_parts(path, 1)


class FigshareProvider:

    def __new__(cls, auth, credentials, settings):
        if settings['container_type'] == 'project':
            return FigshareProjectProvider(auth, credentials, {'project_id': settings['container_id']})
        if settings['container_type'] in ['article', 'fileset']:
            return FigshareArticleProvider(auth, credentials, {'article_id': settings['container_id']})
        raise exceptions.ProviderError('Invalid "container_type" {0}'.format(settings['container_type']))


class BaseFigshareProvider(provider.BaseProvider):

    BASE_URL = 'http://api.figshare.com/v1/my_data'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = oauthlib.oauth1.Client(
            self.credentials['client_token'],
            client_secret=self.credentials['client_secret'],
            resource_owner_key=self.credentials['owner_token'],
            resource_owner_secret=self.credentials['owner_secret'],
        )

    @asyncio.coroutine
    def make_request(self, method, uri, *args, **kwargs):
        signed_uri, signed_headers, _ = self.client.sign(uri, method)
        signed_headers.update(kwargs.pop('headers', {}))
        kwargs['headers'] = signed_headers
        return (yield from super().make_request(method, signed_uri, *args, **kwargs))


class FigshareProjectProvider(BaseFigshareProvider):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_id = self.settings['project_id']

    @asyncio.coroutine
    def _assert_contains_article(self, article_id):
        articles_json = yield from self._list_articles()
        try:
            next(
                each for each in articles_json
                if each['id'] == int(article_id)
            )
        except StopIteration:
            raise exceptions.ProviderError(
                'Article {0} not found'.format(article_id),
                code=http.client.NOT_FOUND,
            )

    @asyncio.coroutine
    def _make_article_provider(self, article_id, check_parent=True):
        article_id = str(article_id)
        if check_parent:
            yield from self._assert_contains_article(article_id)
        settings = {'article_id': article_id}
        return FigshareArticleProvider(self.auth, self.credentials, settings, child=True)

    @asyncio.coroutine
    def _get_project_metadata(self):
        response = yield from self.make_request(
            'GET',
            self.build_url('projects', self.project_id),
            expects=(200, ),
        )
        data = yield from response.json()
        return metadata.FigshareProjectMetadata(data).serialized()

    @asyncio.coroutine
    def _list_articles(self):
        response = yield from self.make_request(
            'GET',
            self.build_url('projects', self.project_id, 'articles'),
            expects=(200, ),
        )
        return (yield from response.json())

    @asyncio.coroutine
    def _get_article_metadata(self, article_id):
        provider = yield from self._make_article_provider(article_id, check_parent=False)
        return (yield from provider.metadata(''))

    @asyncio.coroutine
    def _project_metadata_contents(self):
        articles_json = yield from self._list_articles()
        contents = yield from asyncio.gather(*[
            self._get_article_metadata(each['id'])
            for each in articles_json
        ])
        return [each for each in contents if each]

    @asyncio.coroutine
    def _create_article(self, name):
        response = yield from self.make_request(
            'POST',
            self.build_url('articles'),
            data=json.dumps({
                'title': name,
                'defined_type': 'dataset',
            }),
            headers={'Content-Type': 'application/json'},
            expects=(200, ),
        )
        return (yield from response.json())

    @asyncio.coroutine
    def download(self, path, **kwargs):
        figshare_path = FigshareProjectPath(path)
        provider = yield from self._make_article_provider(figshare_path.article_id)
        return (yield from provider.download(str(figshare_path.child), **kwargs))

    @asyncio.coroutine
    def upload(self, stream, path, **kwargs):
        figshare_path = FigshareProjectPath(path)
        should_create = not figshare_path.file_id
        if should_create:
            article_json = yield from self._create_article(figshare_path.article_id)
            provider = yield from self._make_article_provider(article_json['article_id'], check_parent=False)
            metadata, created = (yield from provider.upload(stream, str(figshare_path), **kwargs))
        else:
            provider = yield from self._make_article_provider(figshare_path.article_id)
            metadata, created = (yield from provider.upload(stream, str(figshare_path.child), **kwargs))
        if should_create:
            yield from provider._add_to_project(self.project_id)
        return metadata, created

    @asyncio.coroutine
    def delete(self, path, **kwargs):
        figshare_path = FigshareProjectPath(path)
        provider = yield from self._make_article_provider(figshare_path.article_id)
        if figshare_path.file_id:
            yield from provider.delete(str(figshare_path.child), **kwargs)
        else:
            yield from provider._remove_from_project(self.project_id)

    @asyncio.coroutine
    def metadata(self, path, **kwargs):
        figshare_path = FigshareProjectPath(path)
        if figshare_path.article_id:
            provider = yield from self._make_article_provider(figshare_path.article_id)
            return (yield from provider.metadata(str(figshare_path.child), **kwargs))
        if figshare_path.is_dir:
            return (yield from self._project_metadata_contents())
        return (yield from self._get_project_metadata())


class FigshareArticleProvider(BaseFigshareProvider):

    def __init__(self, auth, credentials, settings, child=False):
        super().__init__(auth, credentials, settings)
        self.article_id = self.settings['article_id']
        self.child = child

    @asyncio.coroutine
    def _get_article_json(self):
        response = yield from self.make_request(
            'GET',
            self.build_url('articles', self.article_id),
            expects=(200, ),
        )
        data = yield from response.json()
        return data['items'][0]

    @asyncio.coroutine
    def _add_to_project(self, project_id):
        resp = yield from self.make_request(
            'PUT',
            self.build_url('projects', project_id, 'articles'),
            data=json.dumps({'article_id': int(self.article_id)}),
            headers={'Content-Type': 'application/json'},
            expects=(200, ),
        )
        return (yield from resp.json())

    @asyncio.coroutine
    def _remove_from_project(self, project_id):
        resp = yield from self.make_request(
            'DELETE',
            self.build_url('projects', project_id, 'articles'),
            data=json.dumps({'article_id': int(self.article_id)}),
            headers={'Content-Type': 'application/json'},
            expects=(200, ),
        )
        return (yield from resp.json())

    def _serialize_item(self, item, parent=None):
        defined_type = item.get('defined_type')
        files = item.get('files')
        if defined_type == 'fileset':
            metadata_class = metadata.FigshareArticleMetadata
            metadata_kwargs = {}
        elif defined_type and not files:
            # Hide single-file articles with no contents
            return None
        else:
            metadata_class = metadata.FigshareFileMetadata
            metadata_kwargs = {'parent': parent, 'child': self.child}
            if defined_type:
                item = item['files'][0]
        return metadata_class(item, **metadata_kwargs).serialized()

    @asyncio.coroutine
    def download(self, path, accept_url=False, **kwargs):
        file_metadata = yield from self.metadata(path)
        download_url = file_metadata['extra']['downloadUrl']
        if download_url is None:
            raise exceptions.DownloadError('Cannot download private files', code=403)
        if accept_url:
            return download_url
        return (yield from aiohttp.request('GET', download_url))

    @asyncio.coroutine
    def delete(self, path, **kwargs):
        figshare_path = FigshareArticlePath(path)
        yield from self.make_request(
            'DELETE',
            self.build_url('articles', self.article_id, 'files', figshare_path.file_id),
            expects=(200, ),
            throws=exceptions.DeleteError,
        )

    @asyncio.coroutine
    def upload(self, stream, path, **kwargs):
        figshare_path = FigshareArticlePath(path)
        article_json = yield from self._get_article_json()
        stream, boundary, size = figshare_utils.make_upload_data(stream, name='filedata', filename=figshare_path.file_id)
        response = yield from self.make_request(
            'PUT',
            self.build_url('articles', self.article_id, 'files'),
            data=stream,
            headers={
                'Content-Length': str(size),
                'Content-Type': 'multipart/form-data; boundary={0}'.format(boundary.decode()),
            },
            expects=(200, ),
        )
        data = yield from response.json()
        return metadata.FigshareFileMetadata(data, parent=article_json, child=self.child).serialized(), True

    @asyncio.coroutine
    def metadata(self, path, **kwargs):
        figshare_path = FigshareArticlePath(path)
        article_json = yield from self._get_article_json()
        if figshare_path.file_id:
            file_json = figshare_utils.file_or_error(article_json, figshare_path.file_id)
            return metadata.FigshareFileMetadata(file_json, parent=article_json, child=self.child).serialized()
        if figshare_path.is_dir:
            serialized = [
                self._serialize_item(item, parent=article_json)
                for item in article_json['files']
            ]
            return [each for each in serialized if each]
        return self._serialize_item(article_json, parent=article_json)
