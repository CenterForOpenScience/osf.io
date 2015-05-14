import os
import http
import json
import asyncio

import aiohttp
import oauthlib.oauth1

from waterbutler.core import utils
from waterbutler.core import streams
from waterbutler.core import provider
from waterbutler.core import exceptions
from waterbutler.core.path import WaterButlerPath

from waterbutler.providers.figshare import metadata
from waterbutler.providers.figshare import utils as figshare_utils


class FigshareProvider:

    def __new__(cls, auth, credentials, settings):
        if settings['container_type'] == 'project':
            return FigshareProjectProvider(auth, credentials, dict(settings, project_id=settings['container_id']))
        if settings['container_type'] in ('article', 'fileset'):
            return FigshareArticleProvider(auth, credentials, dict(settings, article_id=settings['container_id']))
        raise exceptions.ProviderError('Invalid "container_type" {0}'.format(settings['container_type']))


class BaseFigshareProvider(provider.BaseProvider):
    NAME = 'figshare'
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
    def validate_path(self, path, **kwargs):
        split = path.rstrip('/').split('/')[1:]
        wbpath = WaterButlerPath('/', _ids=(self.settings['project_id'], ), folder=True)

        if split:
            name_or_id = split.pop(0)
            try:
                article = yield from self._assert_contains_article(name_or_id)
            except ValueError:
                return wbpath.child(name_or_id, folder=False)
            except exceptions.ProviderError as e:
                if e.code not in (404, 401):
                    raise
                return wbpath.child(name_or_id, folder=False)

            wbpath = wbpath.child(article['title'], article['id'], folder=True)

        if split:
            provider = yield from self._make_article_provider(article['id'], check_parent=False)
            try:
                return (yield from provider.validate_path('/'.join([''] + split), parent=wbpath))
            except exceptions.ProviderError as e:
                if e.code not in (404, 401):
                    raise
                return wbpath.child(split.pop(0), folder=False)

        return wbpath

    @asyncio.coroutine
    def _assert_contains_article(self, article_id):
        articles_json = yield from self._list_articles()
        try:
            return next(
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
        return data
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
        return (yield from provider.about())

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
        provider = yield from self._make_article_provider(path.parts[1].identifier)
        return (yield from provider.download(path.identifier, **kwargs))

    @asyncio.coroutine
    def upload(self, stream, path, **kwargs):
        if not path.parent.is_root:
            provider = yield from self._make_article_provider(path.parent.identifier)
        else:
            article_json = yield from self._create_article(path.name)
            provider = yield from self._make_article_provider(article_json['article_id'], check_parent=False)
            yield from provider._add_to_project(self.project_id)

        return (yield from provider.upload(stream, path, **kwargs))

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
        if path.is_root:
            return (yield from self._project_metadata_contents())

        provider = yield from self._make_article_provider(path.parts[1].identifier)
        return (yield from provider.metadata(path, **kwargs))

    @asyncio.coroutine
    def revisions(self, path, **kwargs):
        raise exceptions.ProviderError({'message': 'figshare does not support file revisions.'}, code=405)


class FigshareArticleProvider(BaseFigshareProvider):

    def __init__(self, auth, credentials, settings, child=False):
        super().__init__(auth, credentials, settings)
        self.article_id = self.settings['article_id']
        self.child = child

    @asyncio.coroutine
    def validate_path(self, path, parent=None, **kwargs):
        split = path.rstrip('/').split('/')[1:]
        wbpath = parent or WaterButlerPath('/', _ids=(self.article_id, ), folder=True)

        if split:
            name = split.pop(0)

            try:
                fid = int(name)
            except ValueError:
                fid = name

            article_json = yield from self._get_article_json()
            try:
                wbpath = wbpath.child(**next(
                    {
                        '_id': x['id'],
                        'name': x['name'],
                    } for x in article_json['files']
                    if x['id'] == fid
                ))
            except StopIteration:
                wbpath = wbpath.child(name)

        return wbpath

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

    def _serialize_item(self, item, parent):
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
    def about(self):
        article_json = yield from self._get_article_json()
        return self._serialize_item(article_json, article_json)

    @asyncio.coroutine
    def download(self, path, **kwargs):
        """Download a file. Note: Although Figshare may return a download URL,
        the `accept_url` parameter is ignored here, since Figshare does not
        support HTTPS for downloads.

        :param str path: Path to the key you want to download
        :rtype ResponseWrapper:
        """
        file_metadata = yield from self.metadata(path)
        download_url = file_metadata['extra']['downloadUrl']
        if download_url is None:
            raise exceptions.DownloadError(
                'Cannot download private files',
                code=http.client.FORBIDDEN,
            )
        resp = yield from aiohttp.request('GET', download_url)
        return streams.ResponseStreamReader(resp)

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
        article_json = yield from self._get_article_json()

        stream = streams.FormDataStream(
            filedata=(stream, path.name)
        )

        response = yield from self.make_request(
            'PUT',
            self.build_url('articles', self.article_id, 'files'),
            data=stream,
            expects=(200, ),
            headers=stream.headers,
        )

        data = yield from response.json()
        return metadata.FigshareFileMetadata(data, parent=article_json, child=self.child).serialized(), True

    @asyncio.coroutine
    def metadata(self, path, **kwargs):
        article_json = yield from self._get_article_json()

        if path.is_root or path.identifier == int(self.article_id):
            return [x for x in [
                self._serialize_item(item, parent=article_json)
                for item in article_json['files']
            ] if x]

        file_json = figshare_utils.file_or_error(article_json, path.identifier)
        return self._serialize_item(file_json, parent=article_json)

    @asyncio.coroutine
    def revisions(self, path, **kwargs):
        raise exceptions.ProviderError({'message': 'figshare does not support file revisions.'}, code=405)
