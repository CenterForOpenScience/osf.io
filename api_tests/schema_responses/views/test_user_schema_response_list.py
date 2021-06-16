import pytest

from osf_tests.factories import (
    SchemaResponsesFactory,
    NodeFactory,
    RegistrationSchemaFactory,
    AuthUserFactory
)
from django.utils import timezone


@pytest.mark.django_db
class TestUserSchemaResponseList:

    @pytest.fixture()
    def non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_write(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_admin(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node(self):
        return NodeFactory()

    @pytest.fixture()
    def schema(self):
        return RegistrationSchemaFactory()

    @pytest.fixture()
    def schema_response(self, user, user_write, user_admin, node, schema):
        node.add_contributor(user, permissions='read')
        node.add_contributor(user_write, permissions='write')
        node.add_contributor(user_admin, permissions='admin')
        return SchemaResponsesFactory(node=node, schema=schema)

    @pytest.fixture()
    def schema_response_public(self, node, schema):
        return SchemaResponsesFactory(public=timezone.now(), node=node, schema=schema)

    @pytest.fixture()
    def schema_response_deleted(self, node, schema):
        return SchemaResponsesFactory(deleted=timezone.now(), node=node, schema=schema)

    @pytest.fixture()
    def url(self, schema_response):
        return f'/v2/schema_responses/'

    def test_schema_response_list(self, app, schema_response, schema_response_public, schema_response_deleted, user, url):
        resp = app.get(url, auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']

        assert len(data) == 1
        assert schema_response_public._id == data[0]['id']