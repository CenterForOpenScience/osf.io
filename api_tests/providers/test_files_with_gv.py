import pytest
import responses

from osf import features
from api_tests import utils as api_utils
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
)
from waffle.testutils import override_flag
from django.shortcuts import reverse
from api_tests.draft_nodes.views.test_draft_node_files_lists import prepare_mock_wb_response
import pytest
import requests
from http import HTTPStatus

from osf.external.gravy_valet import (
    auth_helpers as gv_auth,
    gv_mocks
)
from osf_tests import factories
from website.settings import GRAVYVALET_URL




@pytest.mark.django_db
class TestWaffleFilesProviderView:
    """
    Just passing id as name, no need to mock GV
    """

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
    def resource(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def addon_files_url(self, resource, provider_gv_id):
        return reverse(
            'nodes:node-storage-provider-detail',
            kwargs={
                'version': 'v2',
                'node_id': resource._id,
                'provider': provider_gv_id
            }
        )

    @responses.activate
    def test_must_have_auth(self, app, resource, addon_files_url):
        res = app.get(addon_files_url, expect_errors=True)
        assert res.status_code == 401

    def test_must_be_contributor(self, app, addon_files_url):
        res = app.get(
            addon_files_url,
            auth=AuthUserFactory().auth,
            expect_errors=True
        )
        assert res.status_code == 403

    def test_get_file_provider(self, app, user, addon_files_url, provider_gv_id):
        res = app.get(addon_files_url, auth=user.auth)

        assert res.status_code == 200
        attributes = res.json['data']['attributes']
        assert attributes['provider'] == str(provider_gv_id)
        assert attributes['name'] == str(provider_gv_id)
        assert res.json['data']['id'] == str(provider_gv_id)


@pytest.mark.django_db
class TestWaffleFilesView:

    @pytest.fixture(autouse=True)
    def override_flag(self):
        with override_flag(features.ENABLE_GV, active=True):
            yield

    @pytest.fixture
    def mock_gv(self):
        mock_gv = gv_mocks.MockGravyValet()
        mock_gv.validate_headers = False
        return mock_gv

    @pytest.fixture
    def external_service(self, mock_gv):
        return mock_gv.configure_mock_provider('box')

    @pytest.fixture
    def external_account(self, mock_gv, user, external_service):
        return mock_gv.configure_mock_account(user, external_service.name)

    @pytest.fixture
    def configured_addon(self, mock_gv, resource, external_account):
        return mock_gv.configure_mock_addon(resource, external_account)

    @pytest.fixture
    def account_one(self, user, external_service, mock_gv):
        return mock_gv.configure_mock_account(user, external_service.name)

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def provider_gv_id(self):
        return 1

    @pytest.fixture()
    def resource(self, user):
        return ProjectFactory(
            creator=user,
            comment_level='public'
        )

    @pytest.fixture()
    def file(self, user, resource):
        return api_utils.create_test_file(
            resource,
            user,
            path='Test path',
            create_guid=False,
            provider=1
        )

    @pytest.fixture()
    def file_url(self, resource, provider_gv_id, file):
        return reverse(
            'nodes:node-files',
            kwargs={
                'version': 'v2',
                'node_id': resource._id,
                'provider': f'{provider_gv_id}/',
                'path': f'{file._id}/'
            }
        )

    @responses.activate
    def test_must_have_auth(self, app, user, file_url, file, provider_gv_id, mock_gv, resource):
        prepare_mock_wb_response(
            node=resource,
            path=file.path + '/',
            provider='1',
            status_code=505  # invalid auth should not reach mock
        )

        res = app.get(
            file_url,
            auth=('invaid', 'auth'),
            expect_errors=True
        )
        assert res.status_code != 505   # invalid auth should not reach mock response
        assert res.status_code == 401

    @responses.activate
    def test_must_be_contributor(self, app, user, file_url, file, provider_gv_id, mock_gv, account_one, configured_addon, resource):
        prepare_mock_wb_response(
            node=resource,
            path=file.path + '/',
            provider='1',
            status_code=403
        )

        res = app.get(
            file_url,
            auth=AuthUserFactory().auth,
            expect_errors=True
        )
        assert res.status_code == 403

    def test_get_file_provider(self, app, user, file_url, file, provider_gv_id, resource, mock_gv, account_one):
        prepare_mock_wb_response(
            path=file.path + '/',
            node=resource,
            provider='1',
            files=[
                {
                    'name': file.name,
                    'path': file.path,
                    'materialized': file.materialized_path,
                    'kind': 'file',
                    'modified': file.modified.isoformat(),
                    'extra': {
                        'extra': 'readAllAboutIt'
                    },
                    'provider': '1'
                },
            ]
        )

        with mock_gv.run_mock():
            res = app.get(file_url, auth=user.auth)

        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        attributes = data[0]['attributes']
        assert attributes['name'] == 'test_file'
        assert attributes['path'] == f'/{file._id}'
        assert attributes['provider'] == str(provider_gv_id)
