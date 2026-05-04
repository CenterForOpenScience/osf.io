import pytest
from elasticsearch_metrics.tests.util import djelme_test_backends
from waffle.testutils import override_switch

from osf import features
from osf_tests.factories import RegistrationFactory, AuthUserFactory
from osf.utils.workflows import RegistrationModerationStates, RegistrationModerationTriggers
from osf.metrics.es8_metrics import RegistriesModerationEventEs8
from tests.utils import capture_notifications


@pytest.fixture
def real_elastic():
    with (
        override_switch(features.ELASTICSEARCH_METRICS, active=True),
        djelme_test_backends(),
    ):
        yield


@pytest.mark.django_db
class TestRegistrationModerationMetrics:

    @pytest.fixture()
    def registration(self):
        return RegistrationFactory()

    def test_record_transitions(self, registration, real_elastic):
        with capture_notifications():
            registration._write_registration_action(
                RegistrationModerationStates.INITIAL,
                RegistrationModerationStates.PENDING,
                registration.creator,
                'Metrics is easy'
            )
        RegistriesModerationEventEs8.refresh()

        assert RegistriesModerationEventEs8.search().count() == 1
        data = RegistriesModerationEventEs8.search().execute()['hits']['hits'][0]['_source']

        assert data['from_state'] == RegistrationModerationStates.INITIAL.db_name
        assert data['to_state'] == RegistrationModerationStates.PENDING.db_name
        assert data['trigger'] == RegistrationModerationTriggers.SUBMIT.db_name
        assert data['user_id'] == registration.creator._id
        assert data['comment'] == 'Metrics is easy'


@pytest.mark.django_db
class TestRegistrationModerationMetricsView:

    @pytest.fixture()
    def registration(self):
        return RegistrationFactory()

    @pytest.fixture
    def user(self):
        user = AuthUserFactory()
        user.is_staff = True
        user.add_system_tag('registries_moderation_metrics')
        user.save()
        return user

    @pytest.fixture
    def other_user(self):
        return AuthUserFactory()

    @pytest.fixture
    def base_url(self):
        return '/_/metrics/registries_moderation/transitions/'

    def test_registries_moderation_view(self, app, user, base_url, registration, real_elastic):
        with capture_notifications():
            registration._write_registration_action(
                RegistrationModerationStates.INITIAL,
                RegistrationModerationStates.PENDING,
                registration.creator,
                'Metrics is easy'
            )
        RegistriesModerationEventEs8.refresh()

        res = app.get(base_url, auth=user.auth, expect_errors=True)
        data = res.json
        assert len(data['buckets']) == 1
        assert data['buckets'][0]['key'] == 'osf'
        assert data['buckets'][0]['doc_count'] == 1
        assert data['buckets'][0]['transitions_with_comments']['doc_count'] == 1
        assert data['buckets'][0]['submissions']['doc_count'] == 1
