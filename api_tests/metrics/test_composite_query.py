import pytest
from datetime import datetime
from osf_tests.factories import (
    PreprintFactory,
    AuthUserFactory
)

from osf.metrics import PreprintDownload
from api.base.settings import API_PRIVATE_BASE as API_BASE
from elasticsearch_dsl import Index


@pytest.fixture()
def preprint():
    return PreprintFactory()


@pytest.fixture()
def user():
    user = AuthUserFactory()
    user.is_staff = True
    user.add_system_tag('preprint_metrics')
    user.save()
    return user


@pytest.fixture
def base_url():
    return '/{}metrics/preprints/'.format(API_BASE)

@pytest.mark.django_db
class TestElasticSearch():

    @pytest.fixture(autouse=True)
    def mock_elastic(self):
        ind = Index('test_2020')
        ind._mapping = PreprintDownload._index._mapping
        PreprintDownload._index = ind
        PreprintDownload._template_name = 'test'
        PreprintDownload._template = 'test_2020'
        ind.save()
        yield
        ind.delete()

    @pytest.fixture()
    def preprint_download(self, preprint):
        return PreprintDownload(
            count=1,
            preprint_id=preprint._id,
            provider_id=preprint.provider._id,
            timestamp=datetime(year=2020, month=1, day=1),
            path='/malcolmjenkinsknockedoutbrandincookcoldinthesuperbowl'
        )

    @pytest.fixture()
    def preprint_download2(self, preprint):
        return PreprintDownload(
            count=1,
            preprint_id=preprint._id,
            provider_id=preprint.provider._id,
            timestamp=datetime(year=2020, month=2, day=1),
        )

    def test_elasticsearch_agg_query(self, app, user, base_url, preprint, preprint_download, preprint_download2):
        post_url = '{}downloads/'.format(base_url)

        payload = {
            'data': {
                'type': 'preprint_metrics',
                'attributes': {
                    'query': {
                        'aggs': {
                            'preprints_by_year': {
                                'composite': {
                                    'sources': [{
                                        'date': {
                                            'date_histogram': {
                                                'field': 'timestamp',
                                                'interval': 'year'
                                            }
                                        }
                                    }]
                                }
                            }
                        }
                    }
                }
            }
        }

        resp = app.post_json_api(post_url, payload, auth=user.auth)

        assert resp.status_code == 200
        assert resp.json['hits']['hits'] == []

        es = preprint_download._get_connection()

        es.index(
            index=preprint_download.get_index_name(),
            doc_type='doc',
            body=preprint_download.to_dict(),
        )
        es.index(
            index=preprint_download2.get_index_name(),
            doc_type='doc',
            body=preprint_download2.to_dict(),
            refresh=True
        )

        resp = app.post_json_api(post_url, payload, auth=user.auth)
        assert resp.status_code == 200
        assert len(resp.json['aggregations']['preprints_by_year']['buckets']) == 1

        payload['data']['attributes']['query']['aggs']['preprints_by_year']['composite']['sources'][0]['date']['date_histogram']['interval'] = 'month'

        resp = app.post_json_api(post_url, payload, auth=user.auth)
        assert len(resp.json['aggregations']['preprints_by_year']['buckets']) == 2
