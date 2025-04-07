
from unittest import mock
import pytest

from waffle.testutils import override_switch

from osf import features
from api.base.settings.defaults import API_BASE
from osf_tests.factories import PreprintFactory


@pytest.mark.django_db
class TestPreprintDetailWithMetrics:
    # enable the ELASTICSEARCH_METRICS switch for all tests
    @pytest.fixture(autouse=True)
    def enable_elasticsearch_metrics(self):
        with override_switch(features.ELASTICSEARCH_METRICS, active=True):
            yield

    @pytest.mark.parametrize(('metric_name', 'metric_class_name'),
    [
        ('downloads', 'PreprintDownload'),
        ('views', 'PreprintView'),
    ])
    def test_preprint_detail_with_downloads(self, app, settings, metric_name, metric_class_name):
        preprint = PreprintFactory()
        url = f'/{API_BASE}preprints/{preprint._id}/?metrics[{metric_name}]=total'

        with mock.patch(f'api.preprints.views.{metric_class_name}.get_count_for_preprint') as mock_get_count_for_preprint:
            mock_get_count_for_preprint.return_value = 42
            res = app.get(url)

        assert res.status_code == 200
        data = res.json
        assert 'metrics' in data['meta']
        assert metric_name in data['meta']['metrics']
        assert data['meta']['metrics'][metric_name] == 42
