import time
import pytest
from website import settings

from osf.metrics import PreprintDownload
from django.core.management import call_command

from osf_tests.factories import (
    PreprintFactory,
    AuthUserFactory
)

from elasticsearch_metrics.field import Keyword

from tests.json_api_test_app import JSONAPITestApp

from api.base import settings as django_settings


@pytest.fixture()
def app():
    return JSONAPITestApp()


@pytest.mark.django_db
class TestReindexingMetrics:

    @pytest.fixture()
    def preprint(self):
        return PreprintFactory()

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def admin(self):
        user = AuthUserFactory()
        user.is_staff = True
        user.add_system_tag('preprint_metrics')
        user.save()
        return user

    @pytest.fixture()
    def url(self):
        return f'{settings.API_DOMAIN}_/metrics/preprints/downloads/'

    @pytest.mark.es
    @pytest.mark.skipif(django_settings.TRAVIS_ENV, reason='Non-deterministic fails on travis')
    def test_reindexing(self, app, url, preprint, user, admin, es6_client):
        preprint_download = PreprintDownload.record_for_preprint(
            preprint,
            user,
            version=1,
            path='/MalcolmJenkinsKnockedBrandinCooksOutColdInTheSuperbowl',
            random_new_field='Hi!'  # Here's our unmapped field! It's a text field by default.
        )
        preprint_download.save()

        query = {
            'aggs': {
                'random_new_field': {
                    'terms': {
                        'field': 'random_new_field',  # Oh no, this is a text field, you can't query it like that!
                    }
                }
            }
        }

        payload = {
            'data': {
                'type': 'preprint_metrics',
                'attributes': {
                    'query': query
                }
            }
        }

        # Hacky way to simulate a re-mapped index template
        index_template = preprint_download._index
        mapping = index_template._mapping
        mapping.properties._params['properties']['random_new_field'] = Keyword(doc_values=True, index=True)
        index_template._mapping._update_from_dict(mapping.to_dict())

        # This should 400 because random_new_field is still stored as a text field despite the our index being remapped.
        res = app.post_json_api(url, payload, auth=admin.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Fielddata is disabled on text fields by default. Set ' \
                                                  'fielddata=true on [random_new_field] in order to load' \
                                                  ' fielddata in memory by uninverting the inverted inde' \
                                                  'x. Note that this can however use significant memory.' \
                                                  ' Alternatively use a keyword field instead.'

        call_command('reindex_es6', f'--indices={preprint_download.meta["index"]}')
        time.sleep(2)

        res = app.post_json_api(url, payload, auth=admin.auth)
        assert res.status_code == 200
        assert res.json['hits']['hits'][0]['_source']['random_new_field'] == 'Hi!'

        # Just checking version number incremented properly
        es6_client.indices.get(f'{preprint_download.meta["index"]}_v2')

        # Just check it was aliased properly
        es6_client.indices.get(f'{preprint_download.meta["index"]}')

        call_command('reindex_es6', f'--indices={preprint_download.meta["index"]}')
        time.sleep(2)

        # Just checking version number incremented properly again
        es6_client.indices.get(f'{preprint_download.meta["index"]}_v3')

        # Just check it was aliased properly again (to the OG index, not the v2 index)
        data = es6_client.indices.get(f'{preprint_download.meta["index"]}')

        assert data[f'{preprint_download.meta["index"]}_v3']['aliases'] == {'osf_preprintdownload_2020': {}}
