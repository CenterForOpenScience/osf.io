import pytest

from api.base.settings.defaults import API_BASE
from osf.models import MetaSchema
from osf_tests.factories import (
    AuthUserFactory,
)
from website.project.metadata.schemas import LATEST_SCHEMA_VERSION


@pytest.mark.django_db
class TestMetaSchemaDetail:

    def test_metaschemas_detail_visibility(self, app):

        user = AuthUserFactory()
        schema = MetaSchema.objects.filter(name='Prereg Challenge', schema_version=LATEST_SCHEMA_VERSION).first()

        #test_pass_authenticated_user_can_retrieve_schema
        url = '/{}metaschemas/{}/'.format(API_BASE, schema._id)
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']['attributes']
        assert data['name'] == 'Prereg Challenge'
        assert data['schema_version'] == 2
        assert data['active']
        assert res.json['data']['id'] == schema._id

        #test_pass_unauthenticated_user_can_view_schemas
        res = app.get(url)
        assert res.status_code == 200

        #test_inactive_metaschema_returned
        inactive_schema = MetaSchema.objects.get(name='Election Research Preacceptance Competition', active=False)
        url = '/{}metaschemas/{}/'.format(API_BASE, inactive_schema._id)
        res = app.get(url)
        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == 'Election Research Preacceptance Competition'
        assert res.json['data']['attributes']['active'] is False

        #test_non_latest_version_metaschema_returned
        old_schema = MetaSchema.objects.get(name='OSF-Standard Pre-Data Collection Registration', schema_version=1)
        url = '/{}metaschemas/{}/'.format(API_BASE, old_schema._id)
        res = app.get(url)
        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == 'OSF-Standard Pre-Data Collection Registration'
        assert res.json['data']['attributes']['schema_version'] == 1

        #test_invalid_metaschema_not_found
        url = '/{}metaschemas/garbage/'.format(API_BASE)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404
