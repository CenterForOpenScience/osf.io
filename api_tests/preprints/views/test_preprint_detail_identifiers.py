from unittest import mock
import responses
import pytest
from django.utils import timezone

from api.base.settings import API_BASE
from website.settings import DOI_FORMAT, CROSSREF_URL
from osf_tests.factories import (
    AuthUserFactory,
    PreprintFactory,
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
class TestPreprintIdentifiers:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def noncontrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def preprint(self, user):
        return PreprintFactory(creator=user)

    @pytest.fixture
    def url(self, preprint):
        return f'/{API_BASE}preprints/{preprint._id}/'

    @pytest.fixture()
    def unpublished_preprint(self, user):
        return PreprintFactory(creator=user, is_published=False)

    @pytest.fixture()
    def unpublished_url(self, unpublished_preprint):
        return f'/{API_BASE}preprints/{unpublished_preprint._id}/'

    @pytest.fixture()
    def preprint_with_article_doi(self, user):
        preprint_article_doi = PreprintFactory(
            creator=user,
            article_doi='10.1235/test',
        )
        return preprint_article_doi

    @pytest.fixture()
    def preprint_with_article_doi_url(self, preprint_with_article_doi):
        return f'/{API_BASE}preprints/{preprint_with_article_doi._id}/'

    def test_update_article_doi_permission_denied_no_auth(self, app, preprint, url):
        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={'article_doi': '10.123/456/789'}
        )

        res = app.patch_json_api(
            url,
            update_payload,
            expect_errors=True
        )
        assert res.status_code == 401

    def test_update_article_doi_permission_denied_noncontrib(self, app, preprint, noncontrib, url):
        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={
                'article_doi': '10.123/456/789'
            }
        )
        res = app.patch_json_api(
            url,
            update_payload,
            auth=noncontrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403

    def test_update_article_doi_permission_denied_read_contrib(self, app, noncontrib, preprint, url):
        preprint.add_contributor(
            noncontrib,
            READ,
            save=True
        )
        res = app.patch_json_api(
            url,
            build_preprint_update_payload(
                preprint._id,
                attributes={'doi': '10.123/456/789'}
            ),
            auth=noncontrib.auth,
            expect_errors=True
        )
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
        app.patch_json_api(
            url,
            build_preprint_update_payload(
                preprint._id,
                attributes={'doi': '10.1234/ASDFASDF'}
            ),
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
        res = app.patch_json_api(
            url,
            build_preprint_update_payload(
                preprint._id,
                attributes={'doi': '10.1235/test'}
            ),
            auth=user.auth
        )
        assert res.json['data']['attributes']['doi'] == '10.1235/test'
        assert res.json['data']['links']['doi'] == 'https://doi.org/10.1235/test'
        assert res.status_code == 200

    def test_update_partial_update_with_article_doi(
            self,
            app,
            user,
            preprint_with_article_doi,
            preprint_with_article_doi_url
    ):
        res = app.patch_json_api(
            preprint_with_article_doi_url,
            build_preprint_update_payload(
                preprint_with_article_doi._id,
                attributes={'custom_citation': 'Hurts so good'}
            ),
            auth=user.auth
        )
        assert res.json['data']['attributes']['doi'] == preprint_with_article_doi.article_doi
        assert res.json['data']['links']['doi'] == 'https://doi.org/10.1235/test'
        assert res.status_code == 200

    @responses.activate
    @mock.patch('osf.models.preprint.update_or_enqueue_on_preprint_updated', mock.Mock())
    def test_update_article_doi_validate_generic_doi(self, app, user, preprint, url):
        responses.add(
            responses.Response(
                responses.POST,
                CROSSREF_URL,
                content_type='text/html;charset=ISO-8859-1',
                status=200,
            ),
        )
        res = app.patch_json_api(
            url,
            build_preprint_update_payload(
                preprint._id,
                attributes={'doi': '10.1235/test'}
            ),
            auth=user.auth
        )
        assert res.json['data']['attributes']['doi'] == '10.1235/test'
        assert res.json['data']['links']['doi'] == 'https://doi.org/10.1235/test'
        assert res.status_code == 200

        # Validate that you can't make a generic OSF DOI
        preprint_doi = DOI_FORMAT.format(
            prefix=preprint.provider.doi_prefix,
            guid=preprint._id
        )

        res = app.patch_json_api(
            url,
            build_preprint_update_payload(
                preprint._id,
                attributes={'doi': preprint_doi}
            ),
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        error_data = res.json['errors']
        assert ' is already associated with this preprint' in error_data[0]['detail']
        preprint.reload()
        assert preprint.article_doi == '10.1235/test'
        resp = app.get(url, auth=user.auth)
        data = resp.json['data']
        assert data['attributes']['doi'] == '10.1235/test'
        assert data['links']['doi'] == 'https://doi.org/10.1235/test'

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

    def test_preprint_detail_shows_article_doi(
            self,
            app,
            user,
            preprint_with_article_doi,
            preprint_with_article_doi_url
    ):
        resp = app.get(
            preprint_with_article_doi_url,
            auth=user.auth
        )
        assert resp.json['data']['attributes']['doi'] == '10.1235/test'

    def test_preprint_detail_update_and_get_article_doi(
            self,
            app,
            user,
            preprint,
            url
    ):
        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={'doi': '10.1235/test'}
        )
        resp = app.patch_json_api(
            url,
            update_payload,
            auth=user.auth
        )
        assert resp.json['data']['attributes']['doi'] == '10.1235/test'
        resp = app.get(
            url,
            auth=user.auth
        )
        assert resp.json['data']['attributes']['doi'] == '10.1235/test'

    def test_preprint_doi_link_absent_in_unpublished_preprints(
            self,
            app,
            user,
            unpublished_preprint,
            unpublished_url
    ):
        resp = app.get(unpublished_url, auth=user.auth)
        assert resp.json['data']['id'] == unpublished_preprint._id
        assert resp.json['data']['attributes']['is_published'] is False
        assert 'preprint_doi' not in resp.json['data']['links'].keys()
        assert resp.json['data']['attributes']['preprint_doi_created'] is None

    def test_published_preprint_doi_link_not_returned_before_doi_request(
            self,
            app,
            user,
            unpublished_preprint,
            unpublished_url
    ):
        unpublished_preprint.is_published = True
        unpublished_preprint.date_published = timezone.now()
        unpublished_preprint.save()
        resp = app.get(unpublished_url, auth=user.auth)
        assert resp.json['data']['id'] == unpublished_preprint._id
        assert resp.json['data']['attributes']['is_published'] is True
        assert 'preprint_doi' not in resp.json['data']['links'].keys()

    def test_published_preprint_doi_link_returned_after_doi_request(
            self,
            app,
            user,
            preprint,
            url
    ):
        expected_doi = DOI_FORMAT.format(prefix=preprint.provider.doi_prefix, guid=preprint._id)
        preprint.set_identifier_values(doi=expected_doi)
        resp = app.get(url, auth=user.auth)
        assert resp.json['data']['id'] == preprint._id
        assert resp.json['data']['attributes']['is_published'] is True
        assert 'preprint_doi' in resp.json['data']['links'].keys()
        assert resp.json['data']['links']['preprint_doi'] == f'https://doi.org/{expected_doi}'
        assert resp.json['data']['attributes']['preprint_doi_created']

    def test_preprint_embed_identifiers(self, app, user, preprint, url):
        embed_url = url + '?embed=identifiers'
        res = app.get(embed_url)
        assert res.status_code == 200
        link = res.json['data']['relationships']['identifiers']['links']['related']['href']
        assert f'{url}identifiers/' in link
