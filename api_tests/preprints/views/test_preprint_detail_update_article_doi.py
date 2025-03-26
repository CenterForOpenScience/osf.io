import mock
import responses
import pytest

from website.settings import DOI_FORMAT, CROSSREF_URL
from osf_tests.factories import AuthUserFactory
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

    def test_update_article_doi_permission_denied(self, app, preprint, url):
        update_payload = build_preprint_update_payload(
            preprint._id,
            attributes={'article_doi': '10.123/456/789'}
        )

        noncontrib = AuthUserFactory()
        res = app.patch_json_api(url, update_payload, auth=noncontrib.auth, expect_errors=True)
        assert res.status_code == 403

        res = app.patch_json_api(url, update_payload, expect_errors=True)
        assert res.status_code == 401

        read_contrib = AuthUserFactory()
        preprint.add_contributor(read_contrib, READ, save=True)
        res = app.patch_json_api(url, update_payload, auth=read_contrib.auth, expect_errors=True)
        assert res.status_code == 403

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
            attributes={'doi': '10.1234/test'}
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
        assert preprint.article_doi == '10.1234/test'

        preprint_detail = app.get(url, auth=user.auth).json['data']
        assert preprint_detail['links']['doi'] == 'https://doi.org/10.1234/test'

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

        app.patch_json_api(url, update_doi_payload, auth=user.auth)

        assert mock_on_preprint_updated.called
