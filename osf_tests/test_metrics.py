import mock
import pytest
from elasticsearch_metrics import metrics

from osf.metrics import MetricMixin
from osf.models import OSFUser
from osf_tests.factories import UserFactory

class DummyMetric(MetricMixin, metrics.Metric):
    count = metrics.Integer(doc_values=True, index=True, required=True)
    user_id = metrics.Keyword(index=True, doc_values=True, required=False)

    class Meta:
        app_label = 'osf'

@pytest.mark.django_db
@mock.patch.object(DummyMetric, '_get_id_to_count')
def test_get_top_by_count(mock_get_id_to_count):
    user1, user2 = UserFactory(), UserFactory()
    mock_get_id_to_count.return_value = {
        user1._id: 41,
        user2._id: 42,
    }

    metric_qs = DummyMetric.get_top_by_count(
        qs=OSFUser.objects.all(),
        model_field='guids___id',
        metric_field='user_id',
        annotation='dummies',
    )

    annotated_user = metric_qs.first()
    assert annotated_user._id == user2._id
    assert annotated_user.dummies == 42
