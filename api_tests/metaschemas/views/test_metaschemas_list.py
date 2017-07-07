import pytest

from api.base.settings.defaults import API_BASE
from osf.models.metaschema import MetaSchema
from osf_tests.factories import (
    AuthUserFactory
)
from website.project.metadata.schemas import LATEST_SCHEMA_VERSION

@pytest.mark.django_db
class TestMetaSchemaList:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def url_metaschemas_list(self):
        return '/{}metaschemas/'.format(API_BASE)

    def test_metaschemas_list_visibility_create_update(self, app, url_metaschemas_list, user):
        #test_pass_authenticated_user_can_view_schemas
        res = app.get(url_metaschemas_list, auth=user.auth)
        assert res.status_code == 200
        assert (
            len(res.json['data']) ==
            MetaSchema.objects.filter(active=True, schema_version=LATEST_SCHEMA_VERSION).count())

        #test_cannot_update_metaschemas
        res = app.put_json_api(url_metaschemas_list, auth=user.auth, expect_errors=True)
        assert res.status_code == 405

        #test_cannot_post_metaschemas
        res = app.post_json_api(url_metaschemas_list, auth=user.auth, expect_errors=True)
        assert res.status_code == 405

        #test_pass_unauthenticated_user_can_view_schemas
        res = app.get(url_metaschemas_list)
        assert res.status_code == 200
