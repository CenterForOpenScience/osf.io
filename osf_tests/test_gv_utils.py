import logging
import pytest
import requests
from http import HTTPStatus

from osf.external.gravy_valet import (
    auth_helpers as gv_auth,
    gv_mocks,
    request_helpers as gv_requests
)
from osf_tests import factories
from website.settings import GRAVYVALET_URL

logger = logging.getLogger(__name__)

@pytest.mark.django_db
class TestMockGV:

    @pytest.fixture
    def test_user(self):
        return factories.AuthUserFactory()

    @pytest.fixture
    def project_one(self, test_user):
        return factories.ProjectFactory(creator=test_user)

    @pytest.fixture
    def project_two(self, test_user):
        return factories.ProjectFactory(creator=test_user)

    @pytest.fixture
    def mock_gv(self, test_user, project_one, project_two):
        mock_gv = gv_mocks.MockGravyValet()
        mock_gv.validate_headers = False
        return mock_gv

    @pytest.fixture
    def provider_one(self, mock_gv):
        return mock_gv.configure_mock_provider(provider_name='foo')

    @pytest.fixture
    def provider_two(self, mock_gv):
        return mock_gv.configure_mock_provider(provider_name='bar')

    @pytest.fixture
    def account_one(self, test_user, provider_one, mock_gv):
        return mock_gv.configure_mock_account(test_user, provider_one.name)

    @pytest.fixture
    def account_two(self, test_user, provider_two, mock_gv):
        return mock_gv.configure_mock_account(test_user, provider_two.name)

    @pytest.fixture
    def account_three(self, provider_one, mock_gv):
        account_owner = factories.AuthUserFactory()
        return mock_gv.configure_mock_account(account_owner, provider_one.name)

    @pytest.fixture
    def addon_one(self, project_one, account_one, mock_gv):
        return mock_gv.configure_mock_addon(project_one, account_one)

    @pytest.fixture
    def addon_two(self, project_one, account_two, mock_gv):
        return mock_gv.configure_mock_addon(project_one, account_two)

    @pytest.fixture
    def addon_three(self, project_two, account_one, mock_gv):
        return mock_gv.configure_mock_addon(project_two, account_one)

    def test_user_route__pk(self, mock_gv, test_user, account_one):
        gv_user_detail_url = gv_requests.USER_DETAIL_ENDPOINT.format(pk=account_one.account_owner_pk)
        logger.critical('DEBUG DEBUG DEBUG')
        logger.critical(gv_user_detail_url)
        logger.critical('\n\n\n')
        with mock_gv.run_mock():
            resp = requests.get(gv_user_detail_url)
        assert resp.status_code == HTTPStatus.OK
        json_data = resp.json()['data']
        assert json_data['id'] == account_one.account_owner_pk
        assert json_data['attributes']['user_uri'] == test_user.get_semantic_iri()
        assert json_data['links']['self'] == gv_user_detail_url
        expected_accounts_link = f'{gv_user_detail_url}/authorized_storage_accounts'
        retrieved_accounts_link = json_data['relationships']['authorized_storage_accounts']['links']['related']
        assert retrieved_accounts_link == expected_accounts_link

    def test_user_route__filter(self, mock_gv, test_user, account_one):
        gv_user_detail_url = gv_requests.USER_DETAIL_ENDPOINT.format(pk=account_one.account_owner_pk)
        gv_user_filtered_list_url = gv_requests.USER_FILTER_ENDPOINT.format(uri=test_user.get_semantic_iri())
        with mock_gv.run_mock():
            detail_resp = requests.get(gv_user_detail_url)
            filtered_list_resp = requests.get(gv_user_filtered_list_url)
        assert filtered_list_resp.status_code == HTTPStatus.OK
        assert filtered_list_resp.json()['data'][0] == detail_resp.json()['data']

    def test_user_route__accounts_link(self, mock_gv, account_one, account_two, account_three):
        gv_user_detail_url = gv_requests.USER_DETAIL_ENDPOINT.format(pk=account_one.account_owner_pk)
        with mock_gv.run_mock():
            user_resp = requests.get(gv_user_detail_url)
            accounts_resp = requests.get(
                user_resp.json()['data']['relationships']['authorized_storage_accounts']['links']['related']
            )
        assert accounts_resp.status_code == HTTPStatus.OK
        json_data = accounts_resp.json()['data']
        # Should not find account_three
        expected_accounts_by_pk = {account.pk: account for account in [account_one, account_two]}
        assert len(json_data) == len(expected_accounts_by_pk)
        for serialized_account in json_data:
            assert serialized_account == expected_accounts_by_pk[serialized_account['id']].serialize()

    def test_resource_route__pk(self, mock_gv, project_one, addon_one):
        gv_resource_detail_url = gv_requests.RESOURCE_DETAIL_ENDPOINT.format(pk=addon_one.resource_pk)
        with mock_gv.run_mock():
            resp = requests.get(gv_resource_detail_url)
        assert resp.status_code == HTTPStatus.OK
        json_data = resp.json()['data']
        assert json_data['id'] == addon_one.resource_pk
        assert json_data['attributes']['resource_uri'] == project_one.get_semantic_iri()
        assert json_data['links']['self'] == gv_resource_detail_url
        expected_addons_link = f'{gv_resource_detail_url}/configured_storage_addons'
        retrieved_addons_link = json_data['relationships']['configured_storage_addons']['links']['related']
        assert retrieved_addons_link == expected_addons_link

    def test_resource_route__filter(self, mock_gv, project_one, addon_one):
        gv_resource_detail_url = gv_requests.RESOURCE_DETAIL_ENDPOINT.format(pk=addon_one.resource_pk)
        gv_resource_filtered_list_url = gv_requests.RESOURCE_FILTER_ENDPOINT.format(uri=project_one.get_semantic_iri())
        with mock_gv.run_mock():
            detail_resp = requests.get(gv_resource_detail_url)
            filtered_list_resp = requests.get(gv_resource_filtered_list_url)
        assert filtered_list_resp.status_code == HTTPStatus.OK
        assert filtered_list_resp.json()['data'][0] == detail_resp.json()['data']

    def test_resource_route__addons_link(self, mock_gv, addon_one, addon_two, addon_three):
        # addon three is the only one connected to project two
        gv_resource_detail_url = gv_requests.RESOURCE_DETAIL_ENDPOINT.format(pk=addon_three.resource_pk)
        with mock_gv.run_mock():
            resource_resp = requests.get(gv_resource_detail_url)
            addons_resp = requests.get(
                resource_resp.json()['data']['relationships']['configured_storage_addons']['links']['related']
            )
        assert addons_resp.status_code == HTTPStatus.OK
        json_data = addons_resp.json()['data']
        assert len(json_data) == 1
        assert json_data[0] == addon_three.serialize()

    def test_account_route(self, mock_gv, account_one):
        gv_account_detail_url = gv_requests.ACCOUNT_ENDPOINT.format(pk=account_one.pk)
        with mock_gv.run_mock():
            resp = requests.get(gv_account_detail_url)
        assert resp.status_code == HTTPStatus.OK
        json_data = resp.json()['data']
        assert json_data['id'] == account_one.pk
        assert json_data['relationships']['account_owner']['data']['id'] == account_one.account_owner_pk
        assert json_data['relationships']['external_storage_service']['data']['id'] == account_one.external_storage_service.pk

    def test_addon_route(self, mock_gv, addon_one):
        gv_addon_detail_url = gv_requests.ADDON_ENDPOINT.format(pk=addon_one.pk)
        with mock_gv.run_mock():
            resp = requests.get(gv_addon_detail_url)
        assert resp.status_code == HTTPStatus.OK
        json_data = resp.json()['data']
        assert json_data['id'] == addon_one.pk
        assert json_data['relationships']['authorized_resource']['data']['id'] == addon_one.resource_pk
        assert json_data['relationships']['base_account']['data']['id'] == addon_one.base_account.pk
        assert json_data['relationships']['external_storage_service']['data']['id'] == addon_one.base_account.external_storage_service.pk


@pytest.mark.django_db
class TestHMACValidation:

    @pytest.fixture
    def mock_gv(self):
        #validate_headers == True by default
        return gv_mocks.MockGravyValet()

    @pytest.fixture
    def contributor(self):
        return factories.AuthUserFactory()

    @pytest.fixture
    def noncontributor(self):
        return factories.AuthUserFactory()

    @pytest.fixture
    def resource(self, contributor):
        return factories.ProjectFactory(creator=contributor)

    @pytest.fixture
    def external_service(self, mock_gv):
        return mock_gv.configure_mock_provider('blarg')

    @pytest.fixture
    def external_account(self, mock_gv, contributor, external_service):
        return mock_gv.configure_mock_account(contributor, external_service.name)

    @pytest.fixture
    def configured_addon(self, mock_gv, resource, external_account):
        return mock_gv.configure_mock_addon(resource, external_account)

    def test_validate_headers__bad_key(self, mock_gv, contributor, external_account):
        request_url = gv_requests.USER_DETAIL_ENDPOINT.format(pk=external_account.account_owner_pk)
        auth_headers = gv_auth.make_gravy_valet_hmac_headers(
            request_url=request_url,
            request_method='GET',
            requesting_user=contributor,
            hmac_key='bad key'
        )
        with mock_gv.run_mock():
            resp = requests.get(request_url, headers=auth_headers)
        assert resp.status_code == HTTPStatus.FORBIDDEN

    def test_validate_headers__missing_headers(self, mock_gv, contributor, external_account):
        request_url = gv_requests.USER_DETAIL_ENDPOINT.format(pk=external_account.account_owner_pk)
        request_url = f'{GRAVYVALET_URL}/v1/user-references/{external_account.account_owner_pk}'
        with mock_gv.run_mock():
            resp = requests.get(request_url)
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    @pytest.mark.parametrize('subpath', ['', '/authorized_storage_accounts'])
    def test_validate_user__success(self, mock_gv, contributor, external_account, subpath):
        base_url = gv_requests.USER_DETAIL_ENDPOINT.format(pk=external_account.account_owner_pk)
        request_url = f'{base_url}{subpath}'
        auth_headers = gv_auth.make_gravy_valet_hmac_headers(
            request_url=request_url,
            request_method='GET',
            requesting_user=contributor
        )
        with mock_gv.run_mock():
            resp = requests.get(request_url, headers=auth_headers)
        assert resp.status_code == HTTPStatus.OK

    @pytest.mark.parametrize('subpath', ['', '/authorized_storage_accounts'])
    def test_validate_user__wrong_user(self, mock_gv, noncontributor, external_account, subpath):
        base_url = gv_requests.USER_DETAIL_ENDPOINT.format(pk=external_account.account_owner_pk)
        request_url = f'{base_url}{subpath}'
        auth_headers = gv_auth.make_gravy_valet_hmac_headers(
            request_url=request_url,
            request_method='GET',
            requesting_user=noncontributor,
        )
        with mock_gv.run_mock():
            resp = requests.get(request_url, headers=auth_headers)
        assert resp.status_code == HTTPStatus.FORBIDDEN

    @pytest.mark.parametrize('subpath', ['', '/authorized_storage_accounts'])
    def test_validate_user__no_user(self, mock_gv, external_account, subpath):
        base_url = gv_requests.USER_DETAIL_ENDPOINT.format(pk=external_account.account_owner_pk)
        request_url = f'{base_url}{subpath}'
        auth_headers = gv_auth.make_gravy_valet_hmac_headers(
            request_url=request_url,
            request_method='GET',
        )
        with mock_gv.run_mock():
            resp = requests.get(request_url, headers=auth_headers)
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    @pytest.mark.parametrize('subpath', ['', '/configured_storage_addons'])
    def test_validate_resource__success(self, mock_gv, contributor, resource, configured_addon, subpath):
        base_url = gv_requests.RESOURCE_DETAIL_ENDPOINT.format(pk=configured_addon.resource_pk)
        request_url = f'{base_url}{subpath}'
        auth_headers = gv_auth.make_gravy_valet_hmac_headers(
            request_url=request_url,
            request_method='GET',
            requesting_user=contributor,
            requested_resource=resource,
        )
        with mock_gv.run_mock():
            resp = requests.get(request_url, headers=auth_headers)
        assert resp.status_code == HTTPStatus.OK

    @pytest.mark.parametrize('subpath', ['', '/configured_storage_addons'])
    def test_validate_resource__wrong_resource(self, mock_gv, contributor, configured_addon, subpath):
        base_url = gv_requests.RESOURCE_DETAIL_ENDPOINT.format(pk=configured_addon.resource_pk)
        request_url = f'{base_url}{subpath}'
        auth_headers = gv_auth.make_gravy_valet_hmac_headers(
            request_url=request_url,
            request_method='GET',
            requesting_user=contributor,
            requested_resource=factories.ProjectFactory(creator=contributor),
        )
        with mock_gv.run_mock():
            resp = requests.get(request_url, headers=auth_headers)
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.parametrize('subpath', ['', '/configured_storage_addons'])
    def test_validate_resource__noncontributor__public_resource(self, mock_gv, noncontributor, resource, configured_addon, subpath):
        resource.is_public = True
        resource.save()
        base_url = gv_requests.RESOURCE_DETAIL_ENDPOINT.format(pk=configured_addon.resource_pk)
        request_url = f'{base_url}{subpath}'
        auth_headers = gv_auth.make_gravy_valet_hmac_headers(
            request_url=request_url,
            request_method='GET',
            requesting_user=noncontributor,
            requested_resource=resource,
        )
        with mock_gv.run_mock():
            resp = requests.get(request_url, headers=auth_headers)
        assert resp.status_code == HTTPStatus.OK

    @pytest.mark.parametrize('subpath', ['', '/configured_storage_addons'])
    def test_validate_resource__noncontributor__private_resource(self, mock_gv, noncontributor, resource, configured_addon, subpath):
        resource.is_public = False
        resource.save()
        base_url = gv_requests.RESOURCE_DETAIL_ENDPOINT.format(pk=configured_addon.resource_pk)
        request_url = f'{base_url}{subpath}'
        auth_headers = gv_auth.make_gravy_valet_hmac_headers(
            request_url=request_url,
            request_method='GET',
            requesting_user=noncontributor,
            requested_resource=resource,
        )
        with mock_gv.run_mock():
            resp = requests.get(request_url, headers=auth_headers)
        assert resp.status_code == HTTPStatus.FORBIDDEN

    @pytest.mark.parametrize('subpath', ['', '/configured_storage_addons'])
    def test_validate_resource__unauthenticated_user__public_resource(self, mock_gv, resource, configured_addon, subpath):
        resource.is_public = True
        resource.save()
        base_url = gv_requests.RESOURCE_DETAIL_ENDPOINT.format(pk=configured_addon.resource_pk)
        request_url = f'{base_url}{subpath}'
        auth_headers = gv_auth.make_gravy_valet_hmac_headers(
            request_url=request_url,
            request_method='GET',
            requested_resource=resource,
        )
        with mock_gv.run_mock():
            resp = requests.get(request_url, headers=auth_headers)
        assert resp.status_code == HTTPStatus.OK

    @pytest.mark.parametrize('subpath', ['', '/configured_storage_addons'])
    def test_validate_resource__unauthenticated_user__private_resource(self, mock_gv, resource, configured_addon, subpath):
        resource.is_public = False
        resource.save()
        base_url = gv_requests.RESOURCE_DETAIL_ENDPOINT.format(pk=configured_addon.resource_pk)
        request_url = f'{base_url}{subpath}'
        auth_headers = gv_auth.make_gravy_valet_hmac_headers(
            request_url=request_url,
            request_method='GET',
            requested_resource=resource,
        )
        with mock_gv.run_mock():
            resp = requests.get(request_url, headers=auth_headers)
        assert resp.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
class TestRequestHelpers:

    @pytest.fixture
    def mock_gv(self):
        #validate_headers == True by default
        return gv_mocks.MockGravyValet()

    @pytest.fixture
    def contributor(self):
        return factories.AuthUserFactory()

    @pytest.fixture
    def noncontributor(self):
        return factories.AuthUserFactory()

    @pytest.fixture
    def resource(self, contributor):
        return factories.ProjectFactory(creator=contributor)

    @pytest.fixture
    def external_service(self, mock_gv):
        return mock_gv.configure_mock_provider('blarg')

    @pytest.fixture
    def external_account(self, mock_gv, contributor, external_service):
        return mock_gv.configure_mock_account(contributor, external_service.name)

    @pytest.fixture
    def configured_addon(self, mock_gv, resource, external_account):
        return mock_gv.configure_mock_addon(resource, external_account)
