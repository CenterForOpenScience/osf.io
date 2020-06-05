import pytest

from api.base.settings.defaults import API_BASE
from osf.models import RegistrationSchema
from osf_tests.factories import (
    AuthUserFactory,
)

pytestmark = pytest.mark.django_db

SCHEMA_VERSION = 2

@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.fixture()
def schema():
    return RegistrationSchema.objects.filter(
        name='Prereg Challenge',
        schema_version=SCHEMA_VERSION
    ).first()


class TestDeprecatedMetaSchemaDetail:
    def test_deprecated_metaschemas_routes(self, app, user, schema):
        # test base /metaschemas/ GET with min version
        url = '/{}metaschemas/?version=2.7'.format(API_BASE)
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200

        # test GET with higher version
        url = '/{}metaschemas/?version=2.8'.format(API_BASE)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'This route has been deprecated. It was last available in version 2.7'

        # test /metaschemas/registrations/
        url = '/{}metaschemas/registrations/{}/?version=2.8'.format(API_BASE, schema._id)
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200

        # test /metaschemas/registrations/ deprecated version
        url = '/{}metaschemas/registrations/{}/?version=2.9'.format(API_BASE, schema._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'This route has been deprecated. It was last available in version 2.8'

@pytest.mark.django_db
class TestRegistrationSchemaDetail:

    def test_schemas_detail_visibility(self, app, user, schema):
        # test_pass_authenticated_user_can_retrieve_schema
        url = '/{}schemas/registrations/{}/'.format(API_BASE, schema._id)
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']['attributes']
        assert data['name'] == 'Prereg Challenge'
        assert data['schema_version'] == 2
        assert res.json['data']['id'] == schema._id

        # test_pass_unauthenticated_user_can_view_schemas
        res = app.get(url)
        assert res.status_code == 200

        # test_inactive_metaschema_returned
        inactive_schema = RegistrationSchema.objects.get(
            name='Election Research Preacceptance Competition', active=False)
        url = '/{}schemas/registrations/{}/'.format(API_BASE, inactive_schema._id)
        res = app.get(url)
        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == 'Election Research Preacceptance Competition'
        assert res.json['data']['attributes']['active'] is False

        # test_invalid_metaschema_not_found
        url = '/{}schemas/registrations/garbage/'.format(API_BASE)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_registration_schema_schema_blocks(self, app, user, schema):
        # test_authenticated_user_can_retrieve_schema_schema_blocks
        url = '/{}schemas/registrations/{}/schema_blocks/'.format(API_BASE, schema._id)
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200

        # test_unauthenticated_user_can_retrieve_schema_schema_blocks
        url = '/{}schemas/registrations/{}/schema_blocks/'.format(API_BASE, schema._id)
        res = app.get(url)
        assert res.status_code == 200

        # test_schema_blocks_detail
        schema_block_id = schema.schema_blocks.first()._id
        url = '/{}schemas/registrations/{}/schema_blocks/{}/'.format(API_BASE, schema._id, schema_block_id)
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == schema_block_id
