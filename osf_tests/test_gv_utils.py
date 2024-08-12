import logging
import pytest
import requests
from http import HTTPStatus

from osf.external.gravy_valet import (
    auth_helpers as gv_auth,
    translations,
    request_helpers as gv_requests,
)
from osf_tests import factories
from osf_tests.external.gravy_valet import gv_fakes
from website.settings import GRAVYVALET_URL

logger = logging.getLogger(__name__)


@pytest.mark.django_db
class TestFakeGV:
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
    def fake_gv(self, test_user, project_one, project_two):
        fake_gv = gv_fakes.FakeGravyValet()
        fake_gv.validate_headers = False
        return fake_gv

    @pytest.fixture
    def provider_one(self, fake_gv):
        return fake_gv.configure_fake_provider(provider_name="foo")

    @pytest.fixture
    def provider_two(self, fake_gv):
        return fake_gv.configure_fake_provider(provider_name="bar")

    @pytest.fixture
    def account_one(self, test_user, provider_one, fake_gv):
        return fake_gv.configure_fake_account(test_user, provider_one.name)

    @pytest.fixture
    def account_two(self, test_user, provider_two, fake_gv):
        return fake_gv.configure_fake_account(test_user, provider_two.name)

    @pytest.fixture
    def account_three(self, provider_one, fake_gv):
        account_owner = factories.AuthUserFactory()
        return fake_gv.configure_fake_account(account_owner, provider_one.name)

    @pytest.fixture
    def addon_one(self, project_one, account_one, fake_gv):
        return fake_gv.configure_fake_addon(project_one, account_one)

    @pytest.fixture
    def addon_two(self, project_one, account_two, fake_gv):
        return fake_gv.configure_fake_addon(project_one, account_two)

    @pytest.fixture
    def addon_three(self, project_two, account_one, fake_gv):
        return fake_gv.configure_fake_addon(project_two, account_one)

    def test_user_route__pk(self, fake_gv, test_user, account_one):
        gv_user_detail_url = gv_requests.USER_DETAIL_ENDPOINT.format(
            pk=account_one.account_owner_pk
        )
        with fake_gv.run_fake():
            resp = requests.get(gv_user_detail_url)
        assert resp.status_code == HTTPStatus.OK
        json_data = resp.json()["data"]
        assert json_data["id"] == account_one.account_owner_pk
        assert (
            json_data["attributes"]["user_uri"] == test_user.get_semantic_iri()
        )
        assert json_data["links"]["self"] == gv_user_detail_url
        expected_accounts_link = (
            f"{gv_user_detail_url}/authorized_storage_accounts"
        )
        retrieved_accounts_link = json_data["relationships"][
            "authorized_storage_accounts"
        ]["links"]["related"]
        assert retrieved_accounts_link == expected_accounts_link

    def test_user_route__filter(self, fake_gv, test_user, account_one):
        gv_user_detail_url = gv_requests.USER_DETAIL_ENDPOINT.format(
            pk=account_one.account_owner_pk
        )
        gv_user_list_url = gv_requests.USER_LIST_ENDPOINT
        with fake_gv.run_fake():
            detail_resp = requests.get(gv_user_detail_url)
            filtered_list_resp = requests.get(
                gv_user_list_url,
                params={"filter[user_uri]": test_user.get_semantic_iri()},
            )
        assert filtered_list_resp.status_code == HTTPStatus.OK
        assert (
            filtered_list_resp.json()["data"][0] == detail_resp.json()["data"]
        )

    def test_user_route__accounts_link(
        self, fake_gv, account_one, account_two, account_three
    ):
        gv_user_detail_url = gv_requests.USER_DETAIL_ENDPOINT.format(
            pk=account_one.account_owner_pk
        )
        with fake_gv.run_fake():
            user_resp = requests.get(gv_user_detail_url)
            accounts_resp = requests.get(
                user_resp.json()["data"]["relationships"][
                    "authorized_storage_accounts"
                ]["links"]["related"]
            )
        assert accounts_resp.status_code == HTTPStatus.OK
        json_data = accounts_resp.json()["data"]
        # Should not find account_three
        expected_accounts_by_pk = {
            account.pk: account for account in [account_one, account_two]
        }
        assert len(json_data) == len(expected_accounts_by_pk)
        for serialized_account in json_data:
            assert (
                serialized_account
                == expected_accounts_by_pk[
                    serialized_account["id"]
                ].serialize()
            )

    def test_resource_route__pk(self, fake_gv, project_one, addon_one):
        gv_resource_detail_url = gv_requests.RESOURCE_DETAIL_ENDPOINT.format(
            pk=addon_one.resource_pk
        )
        with fake_gv.run_fake():
            resp = requests.get(gv_resource_detail_url)
        assert resp.status_code == HTTPStatus.OK
        json_data = resp.json()["data"]
        assert json_data["id"] == addon_one.resource_pk
        assert (
            json_data["attributes"]["resource_uri"]
            == project_one.get_semantic_iri()
        )
        assert json_data["links"]["self"] == gv_resource_detail_url
        expected_addons_link = (
            f"{gv_resource_detail_url}/configured_storage_addons"
        )
        retrieved_addons_link = json_data["relationships"][
            "configured_storage_addons"
        ]["links"]["related"]
        assert retrieved_addons_link == expected_addons_link

    def test_resource_route__filter(self, fake_gv, project_one, addon_one):
        gv_resource_detail_url = gv_requests.RESOURCE_DETAIL_ENDPOINT.format(
            pk=addon_one.resource_pk
        )
        gv_resource_list_url = gv_requests.RESOURCE_LIST_ENDPOINT
        with fake_gv.run_fake():
            detail_resp = requests.get(gv_resource_detail_url)
            filtered_list_resp = requests.get(
                gv_resource_list_url,
                params={
                    "filter[resource_uri]": project_one.get_semantic_iri()
                },
            )
        assert filtered_list_resp.status_code == HTTPStatus.OK
        assert (
            filtered_list_resp.json()["data"][0] == detail_resp.json()["data"]
        )

    def test_resource_route__addons_link(
        self, fake_gv, addon_one, addon_two, addon_three
    ):
        # addon three is the only one connected to project two
        gv_resource_detail_url = gv_requests.RESOURCE_DETAIL_ENDPOINT.format(
            pk=addon_three.resource_pk
        )
        with fake_gv.run_fake():
            resource_resp = requests.get(gv_resource_detail_url)
            addons_resp = requests.get(
                resource_resp.json()["data"]["relationships"][
                    "configured_storage_addons"
                ]["links"]["related"]
            )
        assert addons_resp.status_code == HTTPStatus.OK
        json_data = addons_resp.json()["data"]
        assert len(json_data) == 1
        assert json_data[0] == addon_three.serialize()

    def test_account_route(self, fake_gv, account_one):
        gv_account_detail_url = gv_requests.ACCOUNT_ENDPOINT.format(
            pk=account_one.pk
        )
        with fake_gv.run_fake():
            resp = requests.get(gv_account_detail_url)
        assert resp.status_code == HTTPStatus.OK
        json_data = resp.json()["data"]
        assert json_data["id"] == account_one.pk
        assert (
            json_data["relationships"]["account_owner"]["data"]["id"]
            == account_one.account_owner_pk
        )
        assert (
            json_data["relationships"]["external_storage_service"]["data"][
                "id"
            ]
            == account_one.external_storage_service.pk
        )

    def test_addon_route(self, fake_gv, addon_one):
        gv_addon_detail_url = gv_requests.ADDON_ENDPOINT.format(
            pk=addon_one.pk
        )
        with fake_gv.run_fake():
            resp = requests.get(gv_addon_detail_url)
        assert resp.status_code == HTTPStatus.OK
        json_data = resp.json()["data"]
        assert json_data["id"] == addon_one.pk
        assert (
            json_data["relationships"]["authorized_resource"]["data"]["id"]
            == addon_one.resource_pk
        )
        assert (
            json_data["relationships"]["base_account"]["data"]["id"]
            == addon_one.base_account.pk
        )
        assert (
            json_data["relationships"]["external_storage_service"]["data"][
                "id"
            ]
            == addon_one.base_account.external_storage_service.pk
        )


@pytest.mark.django_db
class TestHMACValidation:
    @pytest.fixture
    def fake_gv(self):
        # validate_headers == True by default
        return gv_fakes.FakeGravyValet()

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
    def external_service(self, fake_gv):
        return fake_gv.configure_fake_provider("blarg")

    @pytest.fixture
    def external_account(self, fake_gv, contributor, external_service):
        return fake_gv.configure_fake_account(
            contributor, external_service.name
        )

    @pytest.fixture
    def configured_addon(self, fake_gv, resource, external_account):
        return fake_gv.configure_fake_addon(resource, external_account)

    def test_validate_headers__bad_key(
        self, fake_gv, contributor, external_account
    ):
        request_url = gv_requests.USER_DETAIL_ENDPOINT.format(
            pk=external_account.account_owner_pk
        )
        auth_headers = gv_auth.make_gravy_valet_hmac_headers(
            request_url=request_url,
            request_method="GET",
            hmac_key="bad key",
            additional_headers=gv_auth.make_permissions_headers(
                requesting_user=contributor
            ),
        )
        with fake_gv.run_fake():
            resp = requests.get(request_url, headers=auth_headers)
        assert resp.status_code == HTTPStatus.FORBIDDEN

    def test_validate_headers__missing_headers(
        self, fake_gv, contributor, external_account
    ):
        request_url = gv_requests.USER_DETAIL_ENDPOINT.format(
            pk=external_account.account_owner_pk
        )
        request_url = f"{GRAVYVALET_URL}/v1/user-references/{external_account.account_owner_pk}"
        with fake_gv.run_fake():
            resp = requests.get(request_url)
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    @pytest.mark.parametrize("subpath", ["", "/authorized_storage_accounts"])
    def test_validate_user__success(
        self, fake_gv, contributor, external_account, subpath
    ):
        base_url = gv_requests.USER_DETAIL_ENDPOINT.format(
            pk=external_account.account_owner_pk
        )
        request_url = f"{base_url}{subpath}"
        auth_headers = gv_auth.make_gravy_valet_hmac_headers(
            request_url=request_url,
            request_method="GET",
            additional_headers=gv_auth.make_permissions_headers(
                requesting_user=contributor
            ),
        )
        with fake_gv.run_fake():
            resp = requests.get(request_url, headers=auth_headers)
        assert resp.status_code == HTTPStatus.OK

    @pytest.mark.parametrize("subpath", ["", "/authorized_storage_accounts"])
    def test_validate_user__wrong_user(
        self, fake_gv, noncontributor, external_account, subpath
    ):
        base_url = gv_requests.USER_DETAIL_ENDPOINT.format(
            pk=external_account.account_owner_pk
        )
        request_url = f"{base_url}{subpath}"
        auth_headers = gv_auth.make_gravy_valet_hmac_headers(
            request_url=request_url,
            request_method="GET",
            additional_headers=gv_auth.make_permissions_headers(
                requesting_user=noncontributor,
            ),
        )
        with fake_gv.run_fake():
            resp = requests.get(request_url, headers=auth_headers)
        assert resp.status_code == HTTPStatus.FORBIDDEN

    @pytest.mark.parametrize("subpath", ["", "/authorized_storage_accounts"])
    def test_validate_user__no_user(self, fake_gv, external_account, subpath):
        base_url = gv_requests.USER_DETAIL_ENDPOINT.format(
            pk=external_account.account_owner_pk
        )
        request_url = f"{base_url}{subpath}"
        auth_headers = gv_auth.make_gravy_valet_hmac_headers(
            request_url=request_url,
            request_method="GET",
        )
        with fake_gv.run_fake():
            resp = requests.get(request_url, headers=auth_headers)
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    @pytest.mark.parametrize("subpath", ["", "/configured_storage_addons"])
    def test_validate_resource__success(
        self, fake_gv, contributor, resource, configured_addon, subpath
    ):
        base_url = gv_requests.RESOURCE_DETAIL_ENDPOINT.format(
            pk=configured_addon.resource_pk
        )
        request_url = f"{base_url}{subpath}"
        auth_headers = gv_auth.make_gravy_valet_hmac_headers(
            request_url=request_url,
            request_method="GET",
            additional_headers=gv_auth.make_permissions_headers(
                requesting_user=contributor,
                requested_resource=resource,
            ),
        )
        with fake_gv.run_fake():
            resp = requests.get(request_url, headers=auth_headers)
        assert resp.status_code == HTTPStatus.OK

    @pytest.mark.parametrize("subpath", ["", "/configured_storage_addons"])
    def test_validate_resource__wrong_resource(
        self, fake_gv, contributor, configured_addon, subpath
    ):
        base_url = gv_requests.RESOURCE_DETAIL_ENDPOINT.format(
            pk=configured_addon.resource_pk
        )
        request_url = f"{base_url}{subpath}"
        auth_headers = gv_auth.make_gravy_valet_hmac_headers(
            request_url=request_url,
            request_method="GET",
            additional_headers=gv_auth.make_permissions_headers(
                requesting_user=contributor,
                requested_resource=factories.ProjectFactory(
                    creator=contributor
                ),
            ),
        )
        with fake_gv.run_fake():
            resp = requests.get(request_url, headers=auth_headers)
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.parametrize("subpath", ["", "/configured_storage_addons"])
    def test_validate_resource__noncontributor__public_resource(
        self, fake_gv, noncontributor, resource, configured_addon, subpath
    ):
        resource.is_public = True
        resource.save()
        base_url = gv_requests.RESOURCE_DETAIL_ENDPOINT.format(
            pk=configured_addon.resource_pk
        )
        request_url = f"{base_url}{subpath}"
        auth_headers = gv_auth.make_gravy_valet_hmac_headers(
            request_url=request_url,
            request_method="GET",
            additional_headers=gv_auth.make_permissions_headers(
                requesting_user=noncontributor,
                requested_resource=resource,
            ),
        )
        with fake_gv.run_fake():
            resp = requests.get(request_url, headers=auth_headers)
        assert resp.status_code == HTTPStatus.OK

    @pytest.mark.parametrize("subpath", ["", "/configured_storage_addons"])
    def test_validate_resource__noncontributor__private_resource(
        self, fake_gv, noncontributor, resource, configured_addon, subpath
    ):
        resource.is_public = False
        resource.save()
        base_url = gv_requests.RESOURCE_DETAIL_ENDPOINT.format(
            pk=configured_addon.resource_pk
        )
        request_url = f"{base_url}{subpath}"
        auth_headers = gv_auth.make_gravy_valet_hmac_headers(
            request_url=request_url,
            request_method="GET",
            additional_headers=gv_auth.make_permissions_headers(
                requesting_user=noncontributor,
                requested_resource=resource,
            ),
        )
        with fake_gv.run_fake():
            resp = requests.get(request_url, headers=auth_headers)
        assert resp.status_code == HTTPStatus.FORBIDDEN

    @pytest.mark.parametrize("subpath", ["", "/configured_storage_addons"])
    def test_validate_resource__unauthenticated_user__public_resource(
        self, fake_gv, resource, configured_addon, subpath
    ):
        resource.is_public = True
        resource.save()
        base_url = gv_requests.RESOURCE_DETAIL_ENDPOINT.format(
            pk=configured_addon.resource_pk
        )
        request_url = f"{base_url}{subpath}"
        auth_headers = gv_auth.make_gravy_valet_hmac_headers(
            request_url=request_url,
            request_method="GET",
            additional_headers=gv_auth.make_permissions_headers(
                requested_resource=resource
            ),
        )
        with fake_gv.run_fake():
            resp = requests.get(request_url, headers=auth_headers)
        assert resp.status_code == HTTPStatus.OK

    @pytest.mark.parametrize("subpath", ["", "/configured_storage_addons"])
    def test_validate_resource__unauthenticated_user__private_resource(
        self, fake_gv, resource, configured_addon, subpath
    ):
        resource.is_public = False
        resource.save()
        base_url = gv_requests.RESOURCE_DETAIL_ENDPOINT.format(
            pk=configured_addon.resource_pk
        )
        request_url = f"{base_url}{subpath}"
        auth_headers = gv_auth.make_gravy_valet_hmac_headers(
            request_url=request_url,
            request_method="GET",
            additional_headers=gv_auth.make_permissions_headers(
                requested_resource=resource,
            ),
        )
        with fake_gv.run_fake():
            resp = requests.get(request_url, headers=auth_headers)
        assert resp.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
class TestRequestHelpers:
    @pytest.fixture
    def fake_gv(self):
        # validate_headers == True by default
        return gv_fakes.FakeGravyValet()

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
    def external_service(self, fake_gv):
        return fake_gv.configure_fake_provider("blarg")

    @pytest.fixture
    def external_account(self, fake_gv, contributor, external_service):
        return fake_gv.configure_fake_account(
            contributor, external_service.name
        )

    @pytest.fixture
    def configured_addon(self, fake_gv, resource, external_account):
        return fake_gv.configure_fake_addon(resource, external_account)

    def test_get_account(
        self, contributor, external_account, external_service, fake_gv
    ):
        with fake_gv.run_fake():
            result = gv_requests.get_account(
                gv_account_pk=external_account.pk, requesting_user=contributor
            )
        retrieved_id = result.resource_id
        assert retrieved_id == external_account.pk
        retrieved_account_name = result.get_attribute("display_name")
        assert retrieved_account_name == external_account.display_name
        retrieved_service_name = result.get_included_attribute(
            include_path=("external_storage_service",),
            attribute_name="display_name",
        )
        assert retrieved_service_name == external_service.name

    def test_get_addon(
        self,
        resource,
        contributor,
        configured_addon,
        external_account,
        external_service,
        fake_gv,
    ):
        with fake_gv.run_fake():
            result = gv_requests.get_addon(
                gv_addon_pk=external_account.pk,
                requested_resource=resource,
                requesting_user=contributor,
            )
        retrieved_id = result.resource_id
        assert retrieved_id == configured_addon.pk
        retrieved_addon_name = result.get_attribute("display_name")
        assert retrieved_addon_name == configured_addon.display_name
        retrieved_service_name = result.get_included_attribute(
            include_path=("base_account", "external_storage_service"),
            attribute_name="display_name",
        )
        assert retrieved_service_name == external_service.name

    def test_get_user_accounts(self, contributor, fake_gv, external_service):
        expected_account_count = 5
        expected_accounts = {
            account.pk: account
            for account in (
                fake_gv.configure_fake_account(
                    contributor, external_service.name
                )
                for _ in range(expected_account_count)
            )
        }
        # unrelated account, will KeyError below if returned in request results
        fake_gv.configure_fake_account(
            factories.UserFactory(), external_service.name
        )
        with fake_gv.run_fake():
            accounts_iterator = gv_requests.iterate_accounts_for_user(
                requesting_user=contributor
            )
            # Need to keep this in the context manager, as generator does not fire request until first access to data
            for retrieved_account in accounts_iterator:
                configured_account = expected_accounts.pop(
                    retrieved_account.resource_id
                )
                assert (
                    retrieved_account.get_attribute("display_name")
                    == configured_account.display_name
                )
                assert (
                    retrieved_account.get_included_attribute(
                        include_path=("external_storage_service",),
                        attribute_name="display_name",
                    )
                    == external_service.name
                )

        assert not expected_accounts  # all accounts popped

    def test_get_resource_addons(self, resource, contributor, fake_gv):
        service_one = fake_gv.configure_fake_provider("argle")
        service_two = fake_gv.configure_fake_provider("bargle")
        account_one = fake_gv.configure_fake_account(
            contributor, service_one.name
        )
        account_two = fake_gv.configure_fake_account(
            contributor, service_two.name
        )
        account_three = fake_gv.configure_fake_account(
            contributor, service_one.name
        )
        addon_one = fake_gv.configure_fake_addon(resource, account_one)
        addon_two = fake_gv.configure_fake_addon(resource, account_two)
        addon_three = fake_gv.configure_fake_addon(resource, account_three)
        # Unrelated Addon, will KeyError below if retured in request results
        fake_gv.configure_fake_addon(
            factories.ProjectFactory(creator=contributor), account_one
        )

        expected_addons = {
            addon.pk: addon for addon in [addon_one, addon_two, addon_three]
        }
        with fake_gv.run_fake():
            addons_iterator = gv_requests.iterate_addons_for_resource(
                requested_resource=resource,
                requesting_user=contributor,
            )
            # Need to keep this in the context manager, as generator does not fire request until first access to data
            for retrieved_addon in addons_iterator:
                configured_addon = expected_addons.pop(
                    retrieved_addon.resource_id
                )
                assert (
                    retrieved_addon.get_attribute("display_name")
                    == configured_addon.display_name
                )
                assert (
                    retrieved_addon.get_included_member(
                        "base_account"
                    ).resource_id
                    == configured_addon.base_account.pk
                )
                assert (
                    retrieved_addon.get_included_attribute(
                        include_path=(
                            "base_account",
                            "external_storage_service",
                        ),
                        attribute_name="display_name",
                    )
                    == configured_addon.base_account.external_storage_service.name
                )

        assert not expected_addons  # all addons popped


@pytest.mark.django_db
class TestEphemeralSettings:
    @pytest.fixture
    def fake_gv(self):
        return gv_fakes.FakeGravyValet()

    @pytest.fixture
    def fake_box(self, fake_gv):
        return fake_gv.configure_fake_provider("box")

    @pytest.fixture
    def contributor(self):
        return factories.AuthUserFactory()

    @pytest.fixture
    def project(self, contributor):
        return factories.ProjectFactory(creator=contributor)

    @pytest.fixture
    def fake_box_account(self, fake_gv, fake_box, contributor):
        return fake_gv.configure_fake_account(contributor, fake_box.name)

    @pytest.fixture
    def fake_box_addon(self, fake_gv, project, fake_box_account):
        return fake_gv.configure_fake_addon(project, fake_box_account)

    def test_make_ephemeral_user_settings(
        self, contributor, fake_box_account, fake_gv
    ):
        with fake_gv.run_fake():
            account_data = gv_requests.get_account(
                gv_account_pk=fake_box_account.pk,
                requesting_user=contributor,
            )
        ephemeral_config = translations.make_ephemeral_user_settings(
            account_data, requesting_user=contributor
        )
        assert ephemeral_config.short_name == "box"
        assert ephemeral_config.gv_id == fake_box_account.pk
        assert ephemeral_config.config.name == "addons.box"

    def test_make_ephemeral_node_settings(
        self, contributor, project, fake_box_addon, fake_gv
    ):
        with fake_gv.run_fake():
            addon_data = gv_requests.get_addon(
                gv_addon_pk=fake_box_addon.pk,
                requesting_user=contributor,
                requested_resource=project,
            )
        ephemeral_config = translations.make_ephemeral_node_settings(
            addon_data, requesting_user=contributor, requested_resource=project
        )
        assert ephemeral_config.short_name == "box"
        assert ephemeral_config.gv_id == fake_box_addon.pk
        assert ephemeral_config.config.name == "addons.box"
        assert ephemeral_config.serialize_waterbutler_settings() == {
            "folder": fake_box_addon.root_folder,
            "service": "box",
        }
