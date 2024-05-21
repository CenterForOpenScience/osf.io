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
    def node(self, user):
        return ProjectFactory(
            creator=user,
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

    @responses.activate
    def test_must_have_auth(self, app, file, node, addon_files_url):
        from api_tests.draft_nodes.views.test_draft_node_files_lists import prepare_mock_wb_response

        prepare_mock_wb_response(
            path=file.path + '/',
            node=node,
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

        res = app.get(addon_files_url, expect_errors=True)
        assert res.status_code == 401

    def test_must_be_contributor(self, app, addon_files_url):
        res = app.get(
            addon_files_url,
            auth=AuthUserFactory().auth,
            expect_errors=True
        )
        assert res.status_code == 403

    def test_get_file_provider(self, app, user, addon_files_url, file, provider_gv_id):
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
            path='Test path',
            create_guid=False,
            provider=1
        )

    @pytest.fixture()
    def file_url(self, node, provider_gv_id, file):
        return reverse(
            'nodes:node-files',
            kwargs={
                'version': 'v2',
                'node_id': node._id,
                'provider': f'{provider_gv_id}/',
                'path': f'{file._id}/'
            }
        )

    @responses.activate
    def test_must_have_auth(self, app, user, file_url, file, provider_gv_id, node):
        prepare_mock_wb_response(
            node=node,
            path=file.path + '/',
            provider='1',
            status_code=505  # invalid auth should not reach mock
        )

        responses.add_passthru('http://192.168.168.167:8004/v1/configured-storage-addons/1/base_account/')
        responses.add_passthru('http://192.168.168.167:8004/v1/authorized-storage-accounts/2/external_storage_service/')

        res = app.get(
            file_url,
            auth=('invaid', 'auth'),
            expect_errors=True
        )
        assert res.status_code != 505   # invalid auth should not reach mock response
        assert res.status_code == 401

    @responses.activate
    def test_must_be_contributor(self, app, user, file_url, file, provider_gv_id, node):
        prepare_mock_wb_response(
            node=node,
            path=file.path + '/',
            provider='1',
            status_code=403
        )

        responses.add_passthru('http://192.168.168.167:8004/v1/configured-storage-addons/1/base_account/')
        responses.add_passthru('http://192.168.168.167:8004/v1/authorized-storage-accounts/2/external_storage_service/')

        res = app.get(
            file_url,
            auth=AuthUserFactory().auth,
            expect_errors=True
        )
        assert res.status_code == 403

    @responses.activate
    def test_get_file_provider(self, app, user, file_url, file, provider_gv_id, node):
        prepare_mock_wb_response(
            path=file.path + '/',
            node=node,
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

        # responses.add_passthru('http://192.168.168.167:7777/v1/resources/2839a/providers/1/66461cb004537100a208ffdd/?meta=True&view_only')
        responses.add_passthru('http://192.168.168.167:8004/v1/configured-storage-addons/1/base_account/')
        responses.add_passthru('http://192.168.168.167:8004/v1/authorized-storage-accounts/2/external_storage_service/')
        res = app.get(file_url, auth=user.auth)

        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        attributes = data[0]['attributes']
        assert attributes['name'] == 'test_file'
        assert attributes['path'] == f'/{file._id}'
        assert attributes['provider'] == str(provider_gv_id)
