import pytest
from waffle.testutils import override_switch

import time
from osf import features
from osf_tests.factories import RegistrationFactory
from osf.utils.workflows import RegistrationModerationStates, RegistrationModerationTriggers
from osf.metrics import RegistriesModerationMetrics

pytestmark = pytest.mark.django_db


@pytest.mark.django_db
class TestRegistrationModerationMetrics:

    @pytest.fixture()
    def registration(self):
        return RegistrationFactory()

    @pytest.fixture(autouse=True)
    def enable_elasticsearch_metrics(self):
        with override_switch(features.ELASTICSEARCH_METRICS, active=True):
            yield

    @pytest.mark.es
    def test_record_transitions(self, registration):
        registration._write_registration_action(
            RegistrationModerationStates.INITIAL,
            RegistrationModerationStates.PENDING,
            registration.creator,
            'Metrics is easy'
        )
        time.sleep(1)

        assert RegistriesModerationMetrics.search().count() == 1
        data = RegistriesModerationMetrics.search().execute()['hits']['hits'][0]['_source']

        assert data['from_state'] == RegistrationModerationStates.INITIAL.db_name
        assert data['to_state'] == RegistrationModerationStates.PENDING.db_name
        assert data['trigger'] == RegistrationModerationTriggers.SUBMIT.db_name
        assert data['user_id'] == registration.creator._id
        assert data['comment'] == 'Metrics is easy'
