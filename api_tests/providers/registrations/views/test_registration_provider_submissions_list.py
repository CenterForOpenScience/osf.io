import pytest
from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    CollectionFactory,
    RegistrationFactory,
    RegistrationProviderFactory,
)
from tests.utils import capture_notifications


@pytest.mark.django_db
class TestRegistrationProviderSubmissionCreate:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration(self, user):
        return RegistrationFactory(creator=user)

    @pytest.fixture()
    def provider(self):
        return RegistrationProviderFactory()

    @pytest.fixture()
    def url(self, provider):
        return f'/{API_BASE}providers/registrations/{provider._id}/submissions/'

    @pytest.fixture()
    def payload(self, registration):
        return {
            'data': {
                'type': 'collection-submissions',
                'attributes': {
                    'guid': registration._id,
                },
            },
        }

    @pytest.fixture()
    def primary_collection(self, user, provider):
        collection = CollectionFactory(creator=user, provider=provider, is_public=True)
        provider.primary_collection = collection
        provider.save()
        return collection

    def test_create_submission_in_primary_collection(self, app, user, registration, primary_collection, url, payload):
        with capture_notifications():
            res = app.post_json_api(url, payload, auth=user.auth)

        assert res.status_code == 201
        assert primary_collection.collectionsubmission_set.filter(guid___id=registration._id).exists()

    def test_cannot_create_submission_without_primary_collection(self, app, user, provider, url, payload):
        assert provider.primary_collection is None

        res = app.post_json_api(url, payload, auth=user.auth, expect_errors=True)

        assert res.status_code == 400
        assert 'has no primary collection' in res.json['errors'][0]['detail']

    def test_create_submission_does_not_lock_provider(self, app, user, primary_collection, url, payload):
        with transaction.atomic(), CaptureQueriesContext(connection) as ctx, capture_notifications():
            res = app.post_json_api(url, payload, auth=user.auth)

        assert res.status_code == 201
        for_update_sql = connection.ops.for_update_sql()
        assert not any(
            query['sql'].startswith('SELECT') and 'osf_abstractprovider' in query['sql'] and for_update_sql in query['sql']
            for query in ctx.captured_queries
        )
