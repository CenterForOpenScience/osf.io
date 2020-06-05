import time
import pytest
from datetime import datetime
from osf_tests.factories import (
    PreprintFactory,
    AuthUserFactory
)

from osf.metrics import PreprintDownload
from api.base.settings import API_PRIVATE_BASE as API_BASE


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


@pytest.mark.es
@pytest.mark.django_db
class TestElasticSearch:

    def test_elasticsearch_agg_query(self, app, user, base_url, preprint):
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

        PreprintDownload.record_for_preprint(
            preprint,
            path=preprint.primary_file.path,
            timestamp=datetime(year=2020, month=1, day=1),
        )
        PreprintDownload.record_for_preprint(
            preprint,
            path=preprint.primary_file.path,
            timestamp=datetime(year=2020, month=2, day=1)
        )
        time.sleep(1)  # gives ES some time to update

        resp = app.post_json_api(post_url, payload, auth=user.auth)
        assert resp.status_code == 200
        assert len(resp.json['aggregations']['preprints_by_year']['buckets']) == 1

        payload['data']['attributes']['query']['aggs']['preprints_by_year']['composite']['sources'][0]['date']['date_histogram']['interval'] = 'month'

        resp = app.post_json_api(post_url, payload, auth=user.auth)
        assert len(resp.json['aggregations']['preprints_by_year']['buckets']) == 2
