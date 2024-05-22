import pytest
import requests

from osf.external.gravy_valet import test_utils
from osf_tests import factories
from website.settings import GRAVYVALET_URL

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
        mock_gv = test_utils.MockGravyValet()
        mock_gv.validate_headers = False
        mock_gv._clear_mappings(include_providers=True)
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
    def addon_one(self, project_one, account_one, mock_gv):
        return mock_gv.configure_mock_addon(project_one, account_one)

    @pytest.fixture
    def addon_two(self, project_one, account_two, mock_gv):
        return mock_gv.configure_mock_addon(project_one, account_two)

    @pytest.fixture
    def addon_three(self, project_two, account_one, mock_gv):
        return mock_gv.configure_mock_addon(project_two, account_one)

    def test_mock_gv__user_route__filter(self, mock_gv, test_user, account_one):
        gv_user_url = f'{GRAVYVALET_URL}/v1/user-references/?filter[user_uri]={test_user.get_semantic_iri()}'
        with mock_gv.run_mock():
            resp = requests.get(gv_user_url)
        assert resp.status_code == 200
        json_data = resp.json()['data'][0]  # implicitly confirm list format
        assert 'user_uri' in json_data['attributes']
        assert 'authorized_storage_accounts' in json_data['relationships']

    def test_mock_gv__user_route__pk(self, mock_gv, test_user, account_one):
        gv_user_url = f'{GRAVYVALET_URL}/v1/user-references/{account_one.account_owner_pk}/'
        with mock_gv.run_mock():
            resp = requests.get(gv_user_url)
        assert resp.status_code == 200
        json_data = resp.json()['data']
        assert 'user_uri' in json_data['attributes']
        assert 'authorized_storage_accounts' in json_data['relationships']
