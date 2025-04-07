from unittest import mock
import responses
import pytest

from api.base.settings import API_BASE
from website.settings import DOI_FORMAT, CROSSREF_URL
from osf_tests.factories import (
    AuthUserFactory,
    PreprintFactory,
    PreprintProviderFactory
)
from osf.utils.permissions import READ

def build_preprint_update_payload(node_id, attributes=None, relationships=None, jsonapi_type='preprints'):
    return {
        'data': {
            'id': node_id,
            'type': jsonapi_type,
            'attributes': attributes,
            'relationships': relationships
        }
    }

@pytest.mark.django_db
@pytest.mark.enable_enqueue_task
class TestPreprintArticleDoiUpdate:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture
    def url(self, preprint):
        return f'/{API_BASE}preprints/{preprint._id}/'

    @pytest.fixture()
    def preprint(self, user):
        return PreprintFactory(
            creator=user,
            provider=PreprintProviderFactory(
                doi_prefix='10.1234/test'
            )
        )

    def test_update_article_doi_permission_denied_no_auth(self, app, preprint, url):
        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={'article_doi': '10.123/456/789'}
        )

        res = app.patch_json_api(url, update_payload, expect_errors=True)
        assert res.status_code == 401

    def test_update_article_doi_permission_denied_noncontrib(self, app, preprint, url):
        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={'article_doi': '10.123/456/789'}
        )
        noncontrib = AuthUserFactory()
        res = app.patch_json_api(url, update_payload, auth=noncontrib.auth, expect_errors=True)
        assert res.status_code == 403

    def test_update_article_doi_permission_denied_read_contrib(self, app, preprint, url):
        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={'article_doi': '10.123/456/789'}
        )
        read_contrib = AuthUserFactory()
        preprint.add_contributor(read_contrib, READ, save=True)
        res = app.patch_json_api(url, update_payload, auth=read_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    @responses.activate
    @mock.patch('osf.models.preprint.update_or_enqueue_on_preprint_updated')
    def test_update_preprint_task_called_on_article_doi_update(
            self,
            mock_on_preprint_updated,
            app,
            user,
            preprint,
            url
    ):
        responses.add(
            responses.Response(
                responses.POST,
                CROSSREF_URL,
                content_type='text/html;charset=ISO-8859-1',
                status=200,
            ),
        )
        update_doi_payload = build_preprint_update_payload(preprint._id, attributes={'doi': '10.1234/ASDFASDF'})

        app.patch_json_api(
            url,
            update_doi_payload,
            auth=user.auth,
        )

        assert mock_on_preprint_updated.called

    @responses.activate
    @mock.patch('osf.models.preprint.update_or_enqueue_on_preprint_updated', mock.Mock())
    def test_update_article_doi(self, app, user, preprint, url):
        responses.add(
            responses.Response(
                responses.POST,
                CROSSREF_URL,
                content_type='text/html;charset=ISO-8859-1',
                status=200,
            ),
        )
        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={'doi': '10.1235/test'}
        )
        res = app.patch_json_api(url, update_payload, auth=user.auth)
        assert res.status_code == 200
        preprint_doi = DOI_FORMAT.format(prefix=preprint.provider.doi_prefix, guid=preprint._id)
        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={'doi': preprint_doi}
        )
        res = app.patch_json_api(url, update_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        error_data = res.json['errors']
        assert ' is already associated with this preprint' in error_data[0]['detail']
        preprint.reload()
        assert preprint.article_doi == '10.1235/test'
        preprint_detail = app.get(url, auth=user.auth).json['data']
        assert preprint_detail['links']['doi'] == 'https://doi.org/10.1235/test'

    @responses.activate
    @mock.patch('osf.models.preprint.update_or_enqueue_on_preprint_updated', mock.Mock())
    def test_article_doi_regex(self, app, user, preprint, url):
        responses.add(
            responses.Response(
                responses.POST,
                CROSSREF_URL,
                content_type='text/html;charset=ISO-8859-1',
                status=200,
            ),
        )
        original_and_stripped_dois = [
            ('10.1235/test', '10.1235/test'),  # ✅ valid
            ('doi.org/10.1235/test', '10.1235/test'),  # ✅ valid
            ('https://10.1235/test', '10.1235/test'),  # ✅ wrong, but helpful to correct user error
            ('https://doi.org/10.1235/test', '10.1235/test'),  # # ✅ valid
            ('10.1312321321/test/tes2/test/13', '10.1312321321/test/tes2/test/13'),  # ✅ valid
            ('10.1235/word1/random/preprint/id/any/other/string///doi',
             '10.1235/word1/random/preprint/id/any/other/string///doi'),  # ✅ valid (more than crossref recommends but technically matches)
            ('10.123/456/789', '10.123/456/789'),  # ✅ valid, if 123 is accepted (it's 3 digits though less than crossref recommends)
            ('https://doi.org/10.1235/osf.io/12345', '10.1235/osf.io/12345'),  # # ✅ valid
            ('https://doi.org/10.1235/test-1234-01-02', '10.1235/test-1234-01-02'),  # # ✅ valid

        ]
        for doi, stripped_doi in original_and_stripped_dois:
            update_payload = build_preprint_update_payload(
                preprint._id,
                attributes={'doi': doi}
            )
            app.patch_json_api(
                url,
                update_payload,
                auth=user.auth
            )
            preprint_detail = app.get(
                url,
                auth=user.auth
            ).json['data']
            assert preprint_detail['links']['doi'] == f'https://doi.org/{stripped_doi}'

    def test_rejects_invalid_doi_format(self, app, user, preprint, url):
        invalid_dois = [
            'not-a-doi',
            '12345',
            'https://example.com/not-a-doi',
            'doi:10.1234',
            '/10.1234/test',
            'https://doi.org/10.1235/',  # ❌ suffix is empty
            '10.1235/',  # ❌ suffix is empty after /
            'http://doi.com/10.1236/test/url/http',  # ❌ invalid prefix
            '10.word/',  # ❌ fails: too short
            'word.10.1234/word2',  # ❌ doesn't start with `10.`
            '10.word/word2/',  # ❌ fails: non-digit after `10.`

        ]
        for invalid_doi in invalid_dois:
            update_payload = build_preprint_update_payload(
                preprint._id,
                attributes={'doi': invalid_doi}
            )
            res = app.patch_json_api(url, update_payload, auth=user.auth, expect_errors=True)
            assert res.status_code == 400
            assert 'Invalid DOI format' in res.json['errors'][0]['detail']
