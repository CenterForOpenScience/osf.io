import pytest

from osf import features
from api.base.settings.defaults import API_BASE
from api_tests import utils as api_utils
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
)
from waffle.testutils import override_flag
from django.shortcuts import reverse


@pytest.mark.django_db
class TestWaffleFilesProviderView:

    @pytest.fixture(autouse=True)
    def override_flag(self):
        with override_flag(features.ENABLE_GV, active=True):
            yield

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def provider_gv_id(self):
        return 1337

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(
            creator=user,
            comment_level='public'
        )

    @pytest.fixture()
    def file(self, user, node):
        return api_utils.create_test_file(
            node,
            user,
            create_guid=False
        )

    @pytest.fixture()
    def addon_files_url(self, node, provider_gv_id):
        return reverse(
            'nodes:node-storage-provider-detail',
            kwargs={
                'version': 'v2',
                'node_id': node._id,
                'provider': provider_gv_id
            }
        )

    def test_must_have_auth(self, app, addon_files_url):
        res = app.get(
            addon_files_url,
            expect_errors=True
        )
        assert res.status_code == 401

    def test_must_be_contributor(self, app, addon_files_url):
        res = app.get(
            addon_files_url,
            auth=AuthUserFactory().auth,
            expect_errors=True
        )
        assert res.status_code == 403

    def test_get_file_provider(self, app, user, addon_files_url, file, provider_gv_id):
        res = app.get(
            addon_files_url,
            auth=user.auth
        )

        assert res.status_code == 200
        attributes = res.json['data']['attributes']
        assert attributes['provider'] == str(provider_gv_id)
        assert attributes['name'] == str(provider_gv_id)
        assert res.json['data']['id'] == f'{file.target._id}:{str(provider_gv_id)}'


@pytest.mark.django_db
class TestWaffleFilesView:

    @pytest.fixture(autouse=True)
    def override_flag(self):
        with override_flag(features.ENABLE_GV, active=True):
            yield

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def provider_gv_id(self):
        return 1

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(
            creator=user,
            comment_level='public'
        )

    @pytest.fixture()
    def file(self, user, node):
        return api_utils.create_test_file(
            node,
            user,
            create_guid=False
        )

    @pytest.fixture()
    def file_url(self, node, provider_gv_id):
        return reverse(
            'nodes:node-files',
            kwargs={
                'version': 'v2',
                'node_id': node._id,
                'provider': str(provider_gv_id) + '/',
                'path': 'test_path/'
            }
        )

    def test_must_have_auth(self, app, file_url):
        res = app.get(
            file_url,
            expect_errors=True
        )
        assert res.status_code == 401

    def test_must_be_contributor(self, app, file_url):
        res = app.get(
            file_url,
            auth=AuthUserFactory().auth,
            expect_errors=True
        )
        assert res.status_code == 403

    def test_get_file_provider(self, app, user, file_url, file, provider_gv_id):
        res = app.get(
            file_url,
            auth=user.auth
        )

        assert res.status_code == 200
        attributes = res.json['data']['attributes']
        assert attributes['provider'] == str(provider_gv_id)
        assert attributes['name'] == str(provider_gv_id)
        assert res.json['data']['id'] == f'{file.target._id}:{str(provider_gv_id)}'


