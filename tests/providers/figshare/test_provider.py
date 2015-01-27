import pytest

from tests.utils import async

import io
import json

import aiohttpretty

from waterbutler.core import streams
from waterbutler.core import exceptions

from waterbutler.providers.figshare import metadata
from waterbutler.providers.figshare import provider


@pytest.fixture
def auth():
    return {
        'name': 'cat',
        'email': 'cat@cat.com',
    }


@pytest.fixture
def credentials():
    return {
        'client_token': 'freddie',
        'client_secret': 'brian',
        'owner_token': 'roger',
        'owner_secret': 'john',
    }


@pytest.fixture
def project_settings():
    return {
        'container_type': 'project',
        'container_id': 'night-at-the-opera',
    }


@pytest.fixture
def article_settings():
    return {
        'container_type': 'article',
        'container_id': 'death-on-two-legs',
    }


@pytest.fixture
def project_provider(auth, credentials, project_settings):
    return provider.FigshareProvider(auth, credentials, project_settings)


@pytest.fixture
def article_provider(auth, credentials, article_settings):
    return provider.FigshareProvider(auth, credentials, article_settings)


@pytest.fixture
def file_content():
    return b'sleepy'


@pytest.fixture
def file_like(file_content):
    return io.BytesIO(file_content)


@pytest.fixture
def file_stream(file_like):
    return streams.FileStreamReader(file_like)


class TestPolymorphism:

    def test_project_provider(self, project_settings, project_provider):
        assert isinstance(project_provider, provider.FigshareProjectProvider)
        assert project_provider.project_id == project_settings['container_id']

    def test_article_provider(self, article_settings, article_provider):
        assert isinstance(article_provider, provider.FigshareArticleProvider)
        assert article_provider.article_id == article_settings['container_id']


@pytest.fixture
def list_project_articles():
    return [
        {'id': 1832, 'title': 'bread.gif', 'description': 'food'},
    ]


@pytest.fixture
def file_metadata():
    return {
        'mime_type': 'text/plain',
        'thumb': None,
        'download_url': 'http://files.figshare.com/1848969/fantine.mp3',
        'name': 'fantine.mp3',
        'size': '42 KB',
        'id': 1848969,
    }


@pytest.fixture
def base_article_metadata(file_metadata):
    return {
        'article_id': 1832,
        'authors': [
            {
                'id': 24601,
                'first_name': 'Jean',
                'last_name': 'Valjean',
                'full_name': 'Jean Valjean',
            },
        ],
        'categories': [],
        'defined_type': 'figure',
        'description': 'food',
        'description_nohtml': 'food',
        'files': [file_metadata],
        'links': [],
        'master_publisher_id': 0,
        'published_date': '16:19, Dec 23, 2014',
        'status': 'Drafts',
        'tags': [],
        'title': '',
        'total_size': '58.16 KB',
        'version': 1,
    }


@pytest.fixture
def article_metadata(base_article_metadata):
    return {'items': [base_article_metadata]}


@pytest.fixture
def upload_metadata():
    return {
        'extension': 'gif',
        'id': 1857195,
        'mime_type': 'image/gif',
        'name': 'barricade.gif',
        'size': '60 KB',
    }


class TestMetadata:

    @async
    @pytest.mark.aiohttpretty
    def test_project_contents(self, project_provider, list_project_articles, article_metadata):
        list_articles_url = project_provider.build_url('projects', project_provider.project_id, 'articles')
        article_metadata_url = project_provider.build_url('articles', str(list_project_articles[0]['id']))
        aiohttpretty.register_json_uri('GET', list_articles_url, body=list_project_articles)
        aiohttpretty.register_json_uri('GET', article_metadata_url, body=article_metadata)
        result = yield from project_provider.metadata('/')
        assert aiohttpretty.has_call(method='GET', uri=list_articles_url)
        assert aiohttpretty.has_call(method='GET', uri=article_metadata_url)
        article_provider = yield from project_provider._make_article_provider(list_project_articles[0]['id'], check_parent=False)
        expected = [
            article_provider._serialize_item(
                article_metadata['items'][0],
                parent=article_metadata['items'][0],
            ),
        ]
        assert result == expected

    @async
    @pytest.mark.aiohttpretty
    def test_project_article_contents(self, project_provider, list_project_articles, article_metadata):
        list_articles_url = project_provider.build_url('projects', project_provider.project_id, 'articles')
        article_metadata_url = project_provider.build_url('articles', str(list_project_articles[0]['id']))
        aiohttpretty.register_json_uri('GET', list_articles_url, body=list_project_articles)
        aiohttpretty.register_json_uri('GET', article_metadata_url, body=article_metadata)
        article_id = list_project_articles[0]['id']
        path = '/{0}/'.format(article_id)
        result = yield from project_provider.metadata(path)
        assert aiohttpretty.has_call(method='GET', uri=list_articles_url)
        assert aiohttpretty.has_call(method='GET', uri=article_metadata_url)
        article_provider = yield from project_provider._make_article_provider(list_project_articles[0]['id'], check_parent=False)
        expected = [
            article_provider._serialize_item(
                article_metadata['items'][0]['files'][0],
                parent=article_metadata['items'][0],
            ),
        ]
        assert result == expected

    @async
    @pytest.mark.aiohttpretty
    def test_project_article_contents_not_in_project(self, project_provider, list_project_articles, article_metadata):
        list_articles_url = project_provider.build_url('projects', project_provider.project_id, 'articles')
        article_metadata_url = project_provider.build_url('articles', str(list_project_articles[0]['id']))
        aiohttpretty.register_json_uri('GET', list_articles_url, body=[])
        aiohttpretty.register_json_uri('GET', article_metadata_url, body=article_metadata)
        article_id = list_project_articles[0]['id']
        path = '/{0}/'.format(article_id)
        with pytest.raises(exceptions.ProviderError) as exc:
            yield from project_provider.metadata(path)
        assert exc.value.code == 404
        assert aiohttpretty.has_call(method='GET', uri=list_articles_url)
        assert not aiohttpretty.has_call(method='GET', uri=article_metadata_url)

    @async
    @pytest.mark.aiohttpretty
    def test_project_article_file(self, project_provider, list_project_articles, article_metadata, file_metadata):
        article_id = str(list_project_articles[0]['id'])
        file_id = file_metadata['id']
        path = '/{0}/{1}'.format(article_id, file_id)
        list_articles_url = project_provider.build_url('projects', project_provider.project_id, 'articles')
        article_metadata_url = project_provider.build_url('articles', article_id)
        aiohttpretty.register_json_uri('GET', list_articles_url, body=list_project_articles)
        aiohttpretty.register_json_uri('GET', article_metadata_url, body=article_metadata)
        result = yield from project_provider.metadata(path)
        expected = metadata.FigshareFileMetadata(file_metadata, parent=article_metadata['items'][0], child=True).serialized()
        assert result == expected


class TestCRUD:

    @async
    @pytest.mark.aiohttpretty
    def test_project_upload(self, project_provider, list_project_articles, base_article_metadata, article_metadata, upload_metadata, file_content, file_stream):
        article_id = str(list_project_articles[0]['id'])
        list_articles_url = project_provider.build_url('projects', project_provider.project_id, 'articles')
        article_metadata_url = project_provider.build_url('articles', article_id)
        article_upload_url = project_provider.build_url('articles', article_id, 'files')
        create_article_url = project_provider.build_url('articles')
        add_article_url = project_provider.build_url('projects', project_provider.project_id, 'articles')
        aiohttpretty.register_json_uri('GET', list_articles_url, body=list_project_articles)
        aiohttpretty.register_json_uri('GET', article_metadata_url, body=article_metadata)
        aiohttpretty.register_json_uri('PUT', article_upload_url, body=upload_metadata)
        aiohttpretty.register_json_uri('POST', create_article_url, body=base_article_metadata)
        aiohttpretty.register_json_uri('PUT', add_article_url)
        file_name = 'barricade.gif'
        path = '/{0}'.format(file_name)
        result, created = yield from project_provider.upload(file_stream, path)
        expected = metadata.FigshareFileMetadata(
            upload_metadata,
            parent=base_article_metadata,
            child=True,
        ).serialized()
        assert aiohttpretty.has_call(
            method='POST',
            uri=create_article_url,
            data=json.dumps({
                'title': 'barricade.gif',
                'defined_type': 'dataset',
            })
        )
        assert aiohttpretty.has_call(method='PUT', uri=article_upload_url)
        assert aiohttpretty.has_call(
            method='PUT',
            uri=add_article_url,
            data=json.dumps({'article_id': int(article_id)})
        )
        assert result == expected

    @async
    @pytest.mark.aiohttpretty
    def test_project_article_upload(self, project_provider, list_project_articles, article_metadata, upload_metadata, file_content, file_stream):
        article_id = str(list_project_articles[0]['id'])
        list_articles_url = project_provider.build_url('projects', project_provider.project_id, 'articles')
        article_metadata_url = project_provider.build_url('articles', article_id)
        article_upload_url = project_provider.build_url('articles', article_id, 'files')
        aiohttpretty.register_json_uri('GET', list_articles_url, body=list_project_articles)
        aiohttpretty.register_json_uri('GET', article_metadata_url, body=article_metadata)
        aiohttpretty.register_json_uri('PUT', article_upload_url, body=upload_metadata)
        file_name = 'barricade.gif'
        path = '/{0}/{1}'.format(article_id, file_name)
        result, created = yield from project_provider.upload(file_stream, path)
        expected = metadata.FigshareFileMetadata(upload_metadata, parent=article_metadata['items'][0], child=True).serialized()
        assert aiohttpretty.has_call(method='PUT', uri=article_upload_url)
        assert result == expected

    @async
    @pytest.mark.aiohttpretty
    def test_project_article_download(self, project_provider, list_project_articles, article_metadata, file_metadata):
        article_id = str(list_project_articles[0]['id'])
        file_id = file_metadata['id']
        path = '/{0}/{1}'.format(article_id, file_id)
        body = b'castle on a cloud'
        list_articles_url = project_provider.build_url('projects', project_provider.project_id, 'articles')
        article_metadata_url = project_provider.build_url('articles', article_id)
        download_url = file_metadata['download_url']
        aiohttpretty.register_json_uri('GET', list_articles_url, body=list_project_articles)
        aiohttpretty.register_json_uri('GET', article_metadata_url, body=article_metadata)
        aiohttpretty.register_uri('GET', download_url, body=body)
        result = yield from project_provider.download(path)
        content = yield from result.read()
        assert content == body

    @async
    @pytest.mark.aiohttpretty
    def test_project_article_download_accept_url(self, project_provider, list_project_articles, article_metadata, file_metadata):
        article_id = str(list_project_articles[0]['id'])
        file_id = file_metadata['id']
        path = '/{0}/{1}'.format(article_id, file_id)
        list_articles_url = project_provider.build_url('projects', project_provider.project_id, 'articles')
        article_metadata_url = project_provider.build_url('articles', article_id)
        aiohttpretty.register_json_uri('GET', list_articles_url, body=list_project_articles)
        aiohttpretty.register_json_uri('GET', article_metadata_url, body=article_metadata)
        result = yield from project_provider.download(path, accept_url=True)
        assert result == file_metadata['download_url']

    @async
    @pytest.mark.aiohttpretty
    def test_project_article_download_not_found(self, project_provider, list_project_articles, article_metadata, file_metadata):
        article_id = str(list_project_articles[0]['id'])
        file_id = str(file_metadata['id'])[::-1]
        path = '/{0}/{1}'.format(article_id, file_id)
        list_articles_url = project_provider.build_url('projects', project_provider.project_id, 'articles')
        article_metadata_url = project_provider.build_url('articles', article_id)
        aiohttpretty.register_json_uri('GET', list_articles_url, body=list_project_articles)
        aiohttpretty.register_json_uri('GET', article_metadata_url, body=article_metadata)
        with pytest.raises(exceptions.ProviderError) as exc:
            yield from project_provider.download(path)
        assert exc.value.code == 404

    @async
    @pytest.mark.aiohttpretty
    def test_article_download(self, article_provider, article_metadata, file_metadata):
        article_id = article_provider.article_id
        file_id = file_metadata['id']
        path = '/{0}'.format(file_id)
        body = b'castle on a cloud'
        article_metadata_url = article_provider.build_url('articles', article_id)
        download_url = file_metadata['download_url']
        aiohttpretty.register_json_uri('GET', article_metadata_url, body=article_metadata)
        aiohttpretty.register_uri('GET', download_url, body=body)
        result = yield from article_provider.download(path)
        content = yield from result.read()
        assert content == body

    @async
    @pytest.mark.aiohttpretty
    def test_project_article_delete(self, project_provider, list_project_articles, article_metadata, file_metadata):
        article_id = str(list_project_articles[0]['id'])
        file_id = str(file_metadata['id'])
        path = '/{0}/{1}'.format(article_id, file_id)
        list_articles_url = project_provider.build_url('projects', project_provider.project_id, 'articles')
        article_metadata_url = project_provider.build_url('articles', article_id)
        article_delete_url = project_provider.build_url('articles', article_id, 'files', file_id)
        aiohttpretty.register_json_uri('GET', list_articles_url, body=list_project_articles)
        aiohttpretty.register_json_uri('GET', article_metadata_url, body=article_metadata)
        aiohttpretty.register_uri('DELETE', article_delete_url)
        result = yield from project_provider.delete(path)
        assert result is None
        assert aiohttpretty.has_call(method='DELETE', uri=article_delete_url)

    @async
    @pytest.mark.aiohttpretty
    def test_project_delete(self, project_provider, list_project_articles, article_metadata):
        article_id = str(list_project_articles[0]['id'])
        path = '/{0}'.format(article_id)
        list_articles_url = project_provider.build_url('projects', project_provider.project_id, 'articles')
        article_metadata_url = project_provider.build_url('articles', article_id)
        aiohttpretty.register_json_uri('GET', list_articles_url, body=list_project_articles)
        aiohttpretty.register_json_uri('GET', article_metadata_url, body=article_metadata)
        aiohttpretty.register_json_uri('DELETE', list_articles_url, body={'article_id': article_id})
        result = yield from project_provider.delete(path)
        assert result is None
        assert aiohttpretty.has_call(method='DELETE', uri=list_articles_url)

    @async
    @pytest.mark.aiohttpretty
    def test_article_delete(self, article_provider, article_metadata, file_metadata):
        article_id = article_provider.article_id
        file_id = str(file_metadata['id'])
        path = '/{0}'.format(file_id)
        article_metadata_url = article_provider.build_url('articles', article_id)
        article_delete_url = article_provider.build_url('articles', article_id, 'files', file_id)
        aiohttpretty.register_json_uri('GET', article_metadata_url, body=article_metadata)
        aiohttpretty.register_uri('DELETE', article_delete_url)
        result = yield from article_provider.delete(path)
        assert result is None
        assert aiohttpretty.has_call(method='DELETE', uri=article_delete_url)
