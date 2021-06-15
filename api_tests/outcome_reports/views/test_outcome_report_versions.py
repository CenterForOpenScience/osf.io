import pytest
from datetime import timedelta

from osf_tests.factories import (
    SchemaResponseFactory,
    NodeFactory,
    RegistrationSchemaFactory,
    AuthUserFactory
)
from django.utils import timezone


@pytest.mark.django_db
class TestSchemaResponseVersions:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node(self):
        return NodeFactory()

    @pytest.fixture()
    def schema(self):
        return RegistrationSchemaFactory()

    @pytest.fixture()
    def schema_response(self, node, schema):
        return SchemaResponseFactory(node=node, schema=schema)

    @pytest.fixture()
    def schema_response_public(self, node, schema):
        return SchemaResponseFactory(public=timezone.now(), node=node, schema=schema)

    @pytest.fixture()
    def schema_response_version(self, node, schema):
        """
        Version that's a day old.
        """
        return SchemaResponseFactory(public=timezone.now() - timedelta(days=1), node=node, schema=schema)

    @pytest.fixture()
    def url(self, schema_response):
        return f'/v2/schema_response/{schema_response._id}/versions/'

    def test_schema_response_versions(self, app, schema_response, schema_response_public, schema_response_version, user, url):
        resp = app.get(url, auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert len(data) == 2
        assert schema_response_public._id == data[0]['id']
        assert schema_response_version._id == data[1]['id']
