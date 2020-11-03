import pytest

from api.base.settings.defaults import API_BASE
from api.caching import settings as cache_settings
from api.caching.utils import storage_usage_cache
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory
)
from osf.utils.permissions import READ, WRITE
from website import settings


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestNodeStorage:
    @pytest.fixture()
    def admin_contributor(self):
        return AuthUserFactory()

    @pytest.fixture()
    def write_contributor(self):
        return AuthUserFactory()

    @pytest.fixture()
    def read_contributor(self):
        return AuthUserFactory()

    @pytest.fixture()
    def non_contributor(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project(self, admin_contributor, write_contributor, read_contributor):
        project = ProjectFactory(
            creator=admin_contributor
        )
        project.add_contributor(write_contributor, WRITE, visible=False)
        project.add_contributor(read_contributor, READ)
        project.save()
        return project

    @pytest.fixture()
    def url(self, project):
        return '/{}nodes/{}/storage/'.format(API_BASE, project._id)

    @pytest.fixture()
    def embed_url(self, project):
        return '/{}nodes/{}/?embed=storage'.format(API_BASE, project._id)

    def test_node_storage_permissions(self, app, url, project,
            write_contributor, read_contributor, non_contributor):

        # Test GET unauthenticated
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        # Test GET non_contributor
        res = app.get(url, auth=non_contributor.auth, expect_errors=True)
        assert res.status_code == 403

        # Test GET read contrib
        res = app.get(url, auth=read_contributor.auth, expect_errors=True)
        assert res.status_code == 403

        # Tests Node Storage for Nodes without Storage Usage Calculated
        res = app.get(url, auth=write_contributor.auth)
        assert res.status_code == 202

        # Tests Node Storage for Nodes no Storage Usage
        res = app.get(url, auth=write_contributor.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert data['attributes']['storage_limit_status'] == 'DEFAULT'
        assert data['attributes']['storage_usage'] == '0'

    def test_node_storage_request_type(self, app, url, project, write_contributor):

        # Test POST not allowed
        res = app.post_json_api(url, auth=write_contributor.auth, expect_errors=True)
        assert res.status_code == 405

    def test_node_storage_with_storage_usage(self, app, url, project, admin_contributor):

        # Test Node Storage with OSFStorage Usage
        storage_usage = (settings.STORAGE_LIMIT_PRIVATE + 1) * settings.GBs
        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=project._id)
        storage_usage_cache.set(key, storage_usage, settings.STORAGE_USAGE_CACHE_TIMEOUT)

        res = app.get(url, auth=admin_contributor.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert data['attributes']['storage_limit_status'] == 'OVER_PRIVATE'
        assert data['attributes']['storage_usage'] == str(storage_usage)

    def test_node_storage_embed(self, app, embed_url, project, admin_contributor):

        # Tests Node Storage Embed
        storage_usage = (settings.STORAGE_LIMIT_PRIVATE + 1) * settings.GBs
        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=project._id)
        storage_usage_cache.set(key, storage_usage, settings.STORAGE_USAGE_CACHE_TIMEOUT)

        res = app.get(embed_url, auth=admin_contributor.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert data['embeds']['storage']['data']['attributes']['storage_limit_status'] == 'OVER_PRIVATE'
        assert data['embeds']['storage']['data']['attributes']['storage_usage'] == str(storage_usage)
